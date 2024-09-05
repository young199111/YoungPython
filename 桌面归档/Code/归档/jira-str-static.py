import pandas as pd
import time
from jira import JIRA


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


def handle_str_changelog(issue):
    shenji_date = None
    fabu_date = None
    yanzheng_date = None
    huihe_date = None
    jieshu_date = None
    for history in issue.changelog.histories:
        created_time = format_timestamp(history.created)
        for item in history.items:
            if not item.fromString:
                continue
            # 基线审计开始时间
            if item.toString == '[运维]基线审计中' or item.toString == '[发布]基线审计、发布检查':
                shenji_date = created_time
            # 排期确认开始时间
            if item.toString == '[发布]生产发布':
                fabu_date = created_time
            # 生产验证开始时间
            if item.fromString == '[发布]生产发布' and item.toString == '[测试]发布验证中':
                yanzheng_date = created_time
            # 代码回合开始时间
            if item.fromString == '[测试]发布验证中' and item.toString == '[运维]代码回合中':
                huihe_date = created_time
            # 发布单流程结束时间
            if item.fromString == '[运维]代码回合中' and item.toString == '[通用]关闭/完成':
                jieshu_date = created_time
    return {
        '基线审计开始时间': shenji_date,
        '生产发布开始时间': fabu_date,
        '生产验证开始时间': yanzheng_date,
        '代码回合开始时间': huihe_date,
        '发布单流程结束时间': jieshu_date
    }


def format_timestamp(timestamp):
    if not timestamp:
        return None
    return pd.to_datetime(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def delta_time(row, start, end):  # df['生产发布时长(分钟)'] = df.apply(delta_time, args=('生产发布开始时间', '生产开始时间'), axis=1)
    if not row[start] or not row[end]:
        return None
    end_time = pd.to_datetime(row[end][0: 20])
    start_time = pd.to_datetime(row[start][0: 20])
    delta = end_time - start_time
    delta_minutes = int(delta.total_seconds() / 60)

    # start_com = pd.to_datetime(row[start][0: 10] + " 20:00:00")
    # end_com = pd.to_datetime(row[end][0: 10] + " 09:30:00")
    # delta_start = start_com - start_time
    # delta_end = end_time - end_com
    # delta_minutes_a = int(delta_start.total_seconds() / 60) + int(delta_end.total_seconds() / 60)
    delta_minutes_a = 30
    print(delta_minutes, delta_minutes_a)
    if row[end][0: 10] == row[start][0: 10]:
        return delta_minutes
    else:
        return delta_minutes_a


def issue_to_dict(issue, issue_type):
    rs = dict()
    if issue_type == 'STR':
        rs = handle_str_changelog(issue)
    return {
        # 'Type': issue.fields.issuetype.name,
        # 'ID': issue.id,
        # '任务单号': issue.id,
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
    out_path = f'./str-{time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())}.xlsx'
    # user_path = f'./UserMap.csv'
    # # user_path = f'./人员Map.csv'
    # _, extension = os.path.splitext(user_path)
    # if extension == '.csv':
    #     df_user = pd_read_csv(user_path)
    # elif extension == '.xlsx':
    #     df_user = pd_read_excel(user_path, 'Sheet1')
    # else:
    #     sys.exit(1)
    # df_user.set_index('责任人', inplace=True)

    jql_str = 'project = STR AND issuetype in (正常提测上线工作流, 紧急提测上线工作流) AND status in ("[通用]关闭/完成", "[发布]产品验收", "[发布]设计验收", "[发布]SIT测试阶段", "[运维]代码回合中", "[通用]部门负责人审批", "[测试]发布验证中", "[发布]待提测", "[通用]测试负责人审批", "[发布]基线审计、发布检查", "[发布]生产发布") AND 计划发布PRD日期 >= 2022-12-01 AND 计划发布PRD日期 <= 2023-03-31 ORDER BY updated DESC, cf[10104] ASC, status ASC, summary ASC'
    sheet_list = [
        ('STR', jql_str)
    ]
    df_list = []
    jira = MyJira(jira_url, username, password)
    for sheet_name, jql in sheet_list:
        sr = jira.search_all_issue(jql, expand='changelog')
        sr_list = [issue_to_dict(i, sheet_name) for i in sr]
        # print(sr_list)
        df = pd_load_list(sr_list)
        if sheet_name == 'STR':
            df['基线审计时长(分钟)'] = df.apply(delta_time, args=('基线审计开始时间', '生产发布开始时间'), axis=1)
            df['生产发布时长(分钟)'] = df.apply(delta_time, args=('生产发布开始时间', '生产验证开始时间'), axis=1)
            df['生产验证时长(分钟)'] = df.apply(delta_time, args=('生产验证开始时间', '代码回合开始时间'), axis=1)
            df['代码回合时长(分钟)'] = df.apply(delta_time, args=('代码回合开始时间', '发布单流程结束时间'), axis=1)
            print(df)
        df_list.append((sheet_name, df))
    write_to_excel(df_list, out_path)


if __name__ == '__main__':
    main()
