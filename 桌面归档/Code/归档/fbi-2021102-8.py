import pandas as pd
import os
import sys
import time
from jira import JIRA
from collections import Counter


class MyJira:
    def __init__(self, url, username, password) -> None:
        self.url = url
        self.username = username
        self.password = password
        self.jira = None
        self.login_jira(self.url, self.username, self.password)

    def login_jira(self, url, username, password, verify=False):
        jira = JIRA(url, basic_auth=(username, password), options={'verify': verify})
        self.jira = jira
        return jira

    def get_all_fields(self):
        return self.jira.fields()
    
    def get_transitions(self, issue):
        return self.jira.transitions(issue)
    
    def get_worklogs(self, issue):
        return self.jira.worklogs(issue)

    def search_issue(self, jql, max_result=-1, **kw):
        search_result = self.jira.search_issues(jql, maxResults=max_result, **kw)
        return search_result

    def search_all_issue(self, jql, count=1000, **kw):
        startAt = 0
        page = 1
        sr = []
        sr_set = self.search_issue(jql, startAt=startAt, max_result=count, **kw)
        sr.extend(sr_set)
        print(f">>>>>>>>page count: {page}, total count: {len(sr)}, start at: {startAt}<<<<<<<<")
        while len(sr_set) == count:
            startAt = page * count
            sr_set = self.search_issue(jql, startAt=startAt, max_result=count, **kw)
            sr.extend(sr_set)
            page += 1
            print(f">>>>>>>>page count: {page}, total count: {len(sr)}, start at: {startAt}<<<<<<<<")
        return sr


def get_attributes(issue, attrs):
    attrs_dict = dict()
    for k, v, extend in attrs:
        if hasattr(issue.fields, v):
            v = getattr(issue.fields, v)
            if v and extend:
                if isinstance(v, list):
                    v = ','.join([getattr(i, extend) for i in v])
                else:
                    v = getattr(v, extend)
            if not v:
                v = ''
        else:
            v = ''
        attrs_dict.update({k: v})
    return attrs_dict


def handle_dtc_changelog(issue):
    schedule_date = None
    dev_date = None
    online_data = None
    for history in issue.changelog.histories:
        created_time = format_timestamp(history.created)
        for item in history.items:
            if not item.fromString:
                continue
            # 排期时间
            if item.fromString == '[通用]待开发' and item.toString == '[通用]开发中':
                schedule_date = created_time
            # 开发时间
            if item.fromString == '[通用]开发中' and item.toString == '[通用]测试中':
                dev_date = created_time
            # 上线时间
            if item.fromString == '[通用]待上线' and item.toString == '[通用]关闭':
                online_data = created_time
    attrs_list = [
        ('计划业务评审时间', 'customfield_11112', ''),
        ('计划转测时间', 'customfield_11514', ''),
        ('计划上线完成时间', 'customfield_11103', ''),
        ('修复的版本', 'fixVersions', 'name') 
    ]
    dicts = get_attributes(issue, attrs_list)
    return {
        '排期时间': schedule_date,
        '开发时间': dev_date,
        '上线时间': online_data,
        **dicts
    }


def handle_bug_changelog(issue):
    fix_date = None
    ls = []
    for history in issue.changelog.histories:
        for item in history.items:
            if not item.fromString:
                continue
            if (f_string := f'{item.fromString}') == '[Bug]待回归' and (t_string := f'{item.toString}') == '[BUG]待修复':
                ls.append(f'{f_string} - {t_string}')
            if item.toString == '[Bug]待回归': 
                fix_date = history.created
    count = Counter(ls).get('[Bug]待回归 - [BUG]待修复', 0)
    attrs_list = [
        ('责任人', 'customfield_11109', 'displayName'),
        ('解决人', 'customfield_10601', 'displayName'),
        ('BUG发现阶段', 'customfield_11106', ''),
        ('BUG产生原因(可多选)', 'customfield_11105', 'value')
    ]
    dicts = get_attributes(issue, attrs_list) 
    return {
        **dicts,
        '缺陷打回次数': count,
        '缺陷修复时间': fix_date
    }


def handle_cnf_changelog(issue):
    attrs_list = [
        ('影响范围', 'customfield_11518', ''),
        ('严重程度', 'customfield_11519', ''),
        ('服务等级', 'customfield_11520', ''),
        ('故障时长', 'customfield_11521', ''),
        ('直接原因', 'customfield_11522', ''),
        ('故障定级', 'customfield_11523', ''),
        ('故障发生时间', 'customfield_11525', ''),
        ('故障责任人', 'customfield_11524', 'displayName'),
        ('技术根因', 'customfield_11526', ''),
        ('管理根因', 'customfield_11527', ''),
        ('纠正措施', 'customfield_11528', ''),
        ('清零措施', 'customfield_11529', ''),
        ('预防措施', 'customfield_11530', ''),
        ('问题引入点分析', 'customfield_11531', ''),
        ('问题控制点分析', 'customfield_11532', ''),
        ('制定管理措施', 'customfield_11533', ''),
        ('改进计划', 'customfield_11534', '')
    ]
    dicts = get_attributes(issue, attrs_list)
    return {
        **dicts
    }


def handle_spt_changelog(issue):
    attrs_list = [
        ('优先级', 'priority', ''),
        ('问题描述(截图+文字)', 'customfield_11117', ''),
        ('问题反馈人', 'customfield_11306', ''),
        ('问题反馈部门', 'customfield_11311', ''),
        ('问题来源', 'customfield_11312', ''),
        ('问题分类', 'customfield_11115', ''),
        ('终端', 'customfield_11320', 'value'),
        ('所属部门', 'customfield_11321', 'value'),
        ('解决人', 'customfield_10601', ''),
        ('解决方案', 'customfield_10708', ''),
    ]
    dicts = get_attributes(issue, attrs_list)
    return {
        **dicts
    }


def format_timestamp(timestamp):
    if not timestamp:
        return None
    return pd.to_datetime(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def delta_time(row, start, end):
    if not row[start] or not row[end]:
        return None
    end_date = pd.to_datetime(row[end][0: 20])
    start_date = pd.to_datetime(row[start][0: 20])
    # print(end_date, start_date)
    delta = end_date - start_date
    delta_day = pd.to_datetime(row[end][0: 10]) - pd.to_datetime(row[start][0: 10]) 
    delta_minutes = int(delta.total_seconds()/60)
    if row[end][0: 10] == row[start][0: 10]:
        return delta_minutes
    else:
        return delta_minutes if delta_minutes < 660 else delta_minutes - 660 * delta_day.days 


def issue_to_dict(issue, issue_type):
    rs = dict()
    if issue_type == 'DTC':
        rs = handle_dtc_changelog(issue)
    if issue_type == 'BUG':
        rs = handle_bug_changelog(issue)
    if issue_type == 'CNF':
        rs = handle_cnf_changelog(issue)
    if issue_type == 'SPT':
        rs = handle_spt_changelog(issue)
    # print(rs)
    return {
        'Type': issue.fields.issuetype.name,
        'ID': issue.id,
        '任务单号': issue.id,
        '关键字': issue.key,
        '任务名称': issue.fields.summary,
        '报告人': issue.fields.reporter.displayName,
        '创建日期': format_timestamp(issue.fields.created),
        '状态': issue.fields.status.name,
        **rs
    }


def delta_day(row, start, end, offset=0):
    if not row[start] or not row[end]:
        return None
    delta_day = pd.to_datetime(row[end][0: 10]) - pd.to_datetime(row[start][0: 10])
    delta_days = delta_day.days + offset
    return delta_days


def pd_read_excel(path, sheet_name):
    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        engine='openpyxl'
    )
    return df


def pd_read_csv(path):
    df = pd.read_csv(
        path
    )
    return df


def pd_load_list(data):
    df = pd.DataFrame(data)
    return df


def write_to_excel(dataframes, path):
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for sheet_name, dataframe in dataframes:
            dataframe.to_excel(writer, sheet_name, index=False)


def set_department(row, department_df, key, column):
    name = row[key]
    if name in department_df.index:
        department = department_df.loc[name][column]
        return department
    return ''


def main():
    jira_url = 'https://jira.znlhzl.org'
    username = 'scrummaster'
    password = 'znlh1234'
    out_path = f'./fbi-{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.xlsx'
    user_path = f'./UserMap.csv'
    # user_path = f'./人员Map.csv'
    _, extension = os.path.splitext(user_path)
    if extension == '.csv':
        df_user = pd_read_csv(user_path)
    elif extension == '.xlsx':
        df_user = pd_read_excel(user_path, 'Sheet1')
    else:
        sys.exit(1)
    df_user.set_index('责任人', inplace=True)

    jql_dtc = 'project = DTC AND issuetype in (产品功能优化, 产品需求) ORDER BY created DESC, priority DESC, updated DESC'
    jql_bug = 'issuetype = "缺陷(Bug)" ORDER BY created DESC'
    jql_cnf = 'project = 现网故障 ORDER BY priority DESC, updated DESC'
    jql_spt = 'project =  技术支持 AND issuetype = 新技术支持工单 AND  created >= "2021/10/01" ORDER BY priority DESC, updated DESC'
    sheet_list = [
        ('DTC', jql_dtc),
        ('BUG', jql_bug),
        ('CNF', jql_cnf),
        ('SPT', jql_spt),
    ]
    df_list = []
    jira = MyJira(jira_url, username, password)
    # all_fields = jira.get_all_fields()
    # for i in all_fields:
    #     print(i['id'], i['name'])
    for sheet_name, jql in sheet_list:    
        sr = jira.search_all_issue(jql, expand='changelog')
        sr_list = [issue_to_dict(i, sheet_name) for i in sr]
        # print(sr_list)
        df = pd_load_list(sr_list)
        if sheet_name == 'DTC':
            df['排期时长(天)'] = df.apply(delta_day, args=('计划业务评审时间', '排期时间'), **{'offset': 1}, axis=1)
            df['转测时长(天)'] = df.apply(delta_day, args=('开发时间', '计划转测时间'), axis=1)
            df['发布时长(天)'] = df.apply(delta_day, args=('上线时间', '计划上线完成时间'), axis=1)
        if sheet_name == 'BUG':
            df['耗时(分钟)'] = df.apply(delta_time, args=('创建日期', '缺陷修复时间'), axis=1)
            df['部门'] = df.apply(set_department, args=(df_user, '责任人', '部门'), axis=1)
        df_list.append((sheet_name, df))
    write_to_excel(df_list, out_path)


if __name__ == '__main__':
    main()