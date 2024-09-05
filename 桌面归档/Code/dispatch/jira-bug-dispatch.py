import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
from jira import JIRA
import pandas as pd
import os
import datetime


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


class DingTalk:
    def __init__(self, url) -> None:
        self.url = url

    def send_message(self, token, secret: str, msgtype: str = 'markdown', title: str = '', text: str = ''):
        timestamp, sign = self.sign(secret)
        data = {
            "msgtype": msgtype,
            "markdown": {
                "title": title,
                "text": text
            }
        }
        res = requests.post(f'{self.url}?access_token={token}&timestamp={timestamp}&sign={sign}', json=data)
        print(res.status_code)

    @classmethod
    def sign(cls, secret):
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign


class LarkTalk:
    def __init__(self, url) -> None:
        self.url = url

    def send_message(self, token, requirement: str = '', date: str = '', text: str = '', reference: str = '',
                     secret: str = '', at_ids: list = [], at_all: bool = False):
        # timestamp, sign = self.sign(secret)
        # print(timestamp, sign)
        bool_flag = True
        data = {
            "msg_type": "interactive",
            "card": {"config": {
                "wide_screen_mode": bool_flag
            },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": bool_flag,
                                "text": {
                                    "content": requirement,
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": bool_flag,
                                "text": {
                                    "content": date,
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": text,
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "elements": [
                            {
                                "content": reference,
                                "tag": "lark_md"
                            }
                        ],
                        "tag": "note"
                    }
                ],
                "header": {
                    "template": "red",
                    "title": {
                        "content": "【提醒】当前需求Bug信息通知",
                        "tag": "plain_text"
                    }
                }
            }
        }
        print(data)
        res = requests.request('POST', f'{self.url}{token}', json=data)
        print(res.status_code, res.content)
        if res.status_code == 200:
            return res.json()
        return False

    @classmethod
    def sign(cls, secret):
        if not secret:
            return None, None
        timestamp = str(round(time.time()) * 1000)
        # timestamp = 100
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign


def all_issue_to_dic(issue):
    return {"name": issue.fields.customfield_11109.displayName,
            "priority": issue.fields.priority.name}


def to_fix_issue_to_dic(issue):
    return {"name": issue.fields.assignee.displayName,
            "priority": issue.fields.priority.name}


def get_to_fix_b4_17(issue):
    issue_date = pd.to_datetime(issue.fields.created).strftime("%Y-%m-%d %H:%M:%S")
    # print(issue_date)
    today = datetime.date.today()
    c_date = pd.to_datetime(str(today) + " 17:00:00").strftime("%Y-%m-%d %H:%M:%S")
    # c_date = pd.to_datetime("2022-08-04 17:00:00").strftime("%Y-%m-%d %H:%M:%S")
    # print(c_date)
    priority = issue.fields.priority.name
    if issue_date < c_date or priority == "P0(致命)" or priority == "P1(严重)":
        return issue
    else:
        return 'remove'


def get_curr_report(issue):
    issue_date = pd.to_datetime(issue.fields.created).strftime("%Y-%m-%d")
    # print(issue_date)
    today = datetime.date.today()
    c_date = pd.to_datetime(str(today)).strftime("%Y-%m-%d")
    # c_date = pd.to_datetime("2022-08-04 17:00:00").strftime("%Y-%m-%d %H:%M:%S")
    # print(c_date)
    if issue_date == c_date:
        return issue
    else:
        return 'remove'


def format_list(_list):
    # 构造这样的数据{"lhq":{total:100,P1(严重):80, P2(一般):20},"zl":{total:152,passed:136}}
    sum_dic2 = {}
    sum_list1 = _list
    for dic1 in sum_list1:
        for name1 in dic1:
            if name1 not in sum_dic2:  # hzy不在sum_dic2这个里面
                if dic1[name1] == "P0(致命)":  # 第一次出现，并且是P0(致命)
                    sum_dic2[name1] = {"total": 1, "P0(致命)": 1, "P1(严重)": 0, "P2(一般)": 0, "P3(轻微)": 0, "P4(建议)": 0}
                elif dic1[name1] == "P1(严重)":  # 第一次出现，并且是P1(严重)
                    sum_dic2[name1] = {"total": 1, "P0(致命)": 0, "P1(严重)": 1, "P2(一般)": 0, "P3(轻微)": 0, "P4(建议)": 0}
                elif dic1[name1] == "P2(一般)":  # 第一次出现，并且是P2(一般)
                    sum_dic2[name1] = {"total": 1, "P0(致命)": 0, "P1(严重)": 0, "P2(一般)": 1, "P3(轻微)": 0, "P4(建议)": 0}
                elif dic1[name1] == "P3(轻微)":  # 第一次出现，并且是P3(轻微)
                    sum_dic2[name1] = {"total": 1, "P0(致命)": 0, "P1(严重)": 0, "P2(一般)": 0, "P3(轻微)": 1, "P4(建议)": 0}
                else:  # 第一次出现，是P4(建议)的
                    sum_dic2[name1] = {"total": 1, "P0(致命)": 0, "P1(严重)": 0, "P2(一般)": 0, "P3(轻微)": 0, "P4(建议)": 1}
            else:  # hzy在sum_dic2这个里面
                if dic1[name1] == "P0(致命)":  # 不是第一次出现，并且是P0(致命)
                    sum_dic2[name1]["total"] += 1
                    sum_dic2[name1]["P0(致命)"] += 1
                elif dic1[name1] == "P1(严重)":  # 不是第一次出现，并且是P1(严重)
                    sum_dic2[name1]["total"] += 1
                    sum_dic2[name1]["P1(严重)"] += 1
                elif dic1[name1] == "P2(一般)":  # 不是第一次出现，并且是P2(一般)
                    sum_dic2[name1]["total"] += 1
                    sum_dic2[name1]["P2(一般)"] += 1
                elif dic1[name1] == "P3(轻微)":  # 不是第一次出现，并且是P3(轻微)
                    sum_dic2[name1]["total"] += 1
                    sum_dic2[name1]["P3(轻微)"] += 1
                else:  # 不是第一次出现，是P4(建议)的
                    sum_dic2[name1]["total"] += 1
                    sum_dic2[name1]["P4(建议)"] += 1
    sum_dic2 = dict(sorted(sum_dic2.items(), key=lambda n: int(n[1]['total']), reverse=True))
    return sum_dic2


def issue_to_str(issue):
    return f'- {issue.key}|{issue.fields.summary}|优先级: {issue.fields.priority.name}|开发: {issue.fields.assignee.displayName}'


def name_to_list(_dic):
    return [
        f'''\n&#62; **<font color='grey'>{i}</font>** |待日清总数：**<font color='red'>{_dic[i]["total"]}</font>** |P0(致命): **<font color='red'>{_dic[i]["P0(致命)"]}</font>** |P1(严重): **<font color='red'>{_dic[i]["P1(严重)"]}</font>** |P2(一般): <font color='red'>{_dic[i]["P2(一般)"]}</font> |P3(轻微): <font color='grey'>{_dic[i]["P3(轻微)"]}</font> |P4(建议): <font color='grey'>{_dic[i]["P4(建议)"]}</font>'''
        for i in _dic]


def all_to_list(_dic, _num):
    all_list = []
    for i, j in enumerate(_dic):
        temp_str = "\n&#62; **<font color='grey'>{}</font>** |累积缺陷总数：**<font color='red'>{}</font>** |占比：**<font color='red'>{:.2%}</font>**".format(
            j, _dic[j], _dic[j] / _num)
        all_list.append(temp_str)
    return all_list


def to_fix_region_to_list(_dic, _num):
    all_list = []
    for i, j in enumerate(_dic):
        temp_str = "\n&#62; **<font color='grey'>{}</font>** |待日清缺陷总数：**<font color='red'>{}</font>** |占比：**<font color='red'>{:.2%}</font>**".format(
            j, _dic[j], _dic[j] / _num)
        all_list.append(temp_str)
    return all_list


def to_check_to_list(_dic):
    to_check_list = []
    for i, j in enumerate(_dic[0]):
        temp_str = "\n&#62; **<font color='grey'>{}</font>** |累积缺陷总数：**<font color='red'>{}</font>**".format(j,
                                                                                                             _dic[0][j])
        to_check_list.append(temp_str)
    return to_check_list


def pd_read_csv(path):
    df = pd.read_csv(
        path
    )
    return df


def pd_read_excel(path, sheet_name):
    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        engine='openpyxl'
    )
    return df


def set_department(row, department_df, key, column):
    name = row[key]
    if name in department_df.index:
        department = department_df.loc[name][column]
        return department
    return '未知'


def name_to_region_list(_dic):
    user_path = f'./UserMap.csv'
    _, extension = os.path.splitext(user_path)
    if extension == '.csv':
        df_user = pd_read_csv(user_path)
    elif extension == '.xlsx':
        df_user = pd_read_excel(user_path, 'Sheet1')
    else:
        sys.exit(1)
    df_user.set_index('责任人', inplace=True)

    tmp_list = []
    for i in _dic:
        tmp_dic = {'责任人': i,
                   'total': _dic[i]['total'],
                   'P0': _dic[i]['P0(致命)'],
                   'P1': _dic[i]['P1(严重)'],
                   'P2': _dic[i]['P2(一般)'],
                   'P3': _dic[i]['P3(轻微)'],
                   'P4': _dic[i]['P4(建议)']}
        tmp_list.append(tmp_dic)
    df = pd.DataFrame(tmp_list)
    # print(df)
    df['部门'] = df.apply(set_department, args=(df_user, '责任人', '部门'), axis=1)
    print(df)
    # df_merge = df.groupby('部门').agg({'total': 'sum', 'P0': 'sum','P1': 'sum','P2': 'sum','P3': 'sum','P4': 'sum'})
    df_merge = df['total'].groupby(df['部门']).sum()
    # print(df_merge)
    f_dic = dict(df_merge)
    f_dic = dict(sorted(f_dic.items(), key=lambda n: int(n[1]), reverse=True))
    # print(f_dic)
    return f_dic, df['total'].sum()


def main():
    jira_url = 'https://jira.znlhzl.org'
    username = 'scrummaster'
    password = 'znlh1234'
    # ding_url = 'https://oapi.dingtalk.com/robot/send'
    lark_url = 'https://open.feishu.cn/open-apis/bot/v2/hook/'

    # groups = [
    #     # CCS
    #     ('8511f600658fdcee351fb414fcb3fa4c36787891f303392e8e71c504bd113164',
    #      'SEC7c37822cbae61d59cb567a2bbe2e1d7879cf1dd88fc6af2356bf3ac6e9b8b8cc')
    # ]

    # ding = DingTalk(ding_url)

    # token,
    # requirement, "**需求**\n呼叫中心（1128）"
    # date, "**时间**\n2021-07-25 15:35:00"
    # reference
    req_name = "排班表优化（1206）"
    date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    groups = [
        ('e217afc9-5638-4393-9f02-86203e63e4b5', '**需求**\n' + req_name, '**时间**\n' + date_time,
         '[数据来源Jira](https://jira.znlhzl.org/)')
    ]

    lark = LarkTalk(lark_url)

    jira = MyJira(jira_url, username, password)

    # 客端CRM
    all_list = [
        'issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复", "[通用]挂起", "[Bug]待回归", "[Bug]正常关闭", "[Bug]待测试确认", "[Bug]待产品确认") AND text ~ 【排班表优化】 AND created >= 2022-11-01 AND reporter in (shijiaqi, lijingjing, yanmin, geyaru, wangweina, wangweina2, wangyang7) ORDER BY status ASC, cf[11109] DESC, assignee ASC'
    ]
    fixed_list = [
        'issuetype = "缺陷(Bug)" AND status in ("[通用]挂起", "[Bug]待回归", "[Bug]正常关闭") AND text ~ 【排班表优化】 AND created >= 2022-11-01 AND reporter in (shijiaqi, lijingjing, yanmin, geyaru, wangweina, wangweina2, wangyang7) ORDER BY status ASC, cf[11109] DESC, assignee ASC'
    ]
    to_fix_list = [
        'issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND text ~ 【排班表优化】 AND created >= 2022-11-01 AND reporter in (shijiaqi, lijingjing, yanmin, geyaru, wangweina, wangweina2, wangyang7) ORDER BY status ASC, cf[11109] DESC, assignee ASC'
    ]
    to_check_list = [
        'issuetype = "缺陷(Bug)" AND status in ("[Bug]待测试确认", "[Bug]待产品确认") AND text ~ 【排班表优化】 AND created >= 2022-11-01 AND reporter in (shijiaqi, lijingjing, yanmin, geyaru, wangweina, wangweina2, wangyang7) ORDER BY status ASC, cf[11109] DESC, assignee ASC'
    ]

    print("开始全部数据处理")
    sr_all = []
    for i in all_list:
        sr_all_tmp = jira.search_all_issue(i)
        sr_all.extend(sr_all_tmp)
    sr_curr_report = [get_curr_report(i) for i in sr_all]
    # print("*"*10, len(sr_curr_report), sr_curr_report)
    j = 0
    for i in range(len(sr_curr_report)):
        if sr_curr_report[j] == 'remove':
            sr_curr_report.pop(j)
        else:
            j += 1
    # print("="*10, len(sr_curr_report), sr_curr_report)
    sr_list_all = [all_issue_to_dic(i) for i in sr_all]
    # 构造这样的数据[{"lhq":"P1(严重)"},{"lhq":"P1(严重)"}]
    sum_list_all = []
    for i in sr_list_all:
        sum_dic_all = {i["name"]: i["priority"]}
        sum_list_all.append(sum_dic_all)
    name_dic_all = format_list(sum_list_all)
    # print("=" * 10, name_dic_all)
    if name_dic_all:
        f_all_dic, all_num = name_to_region_list(name_dic_all)
        name_list_all = all_to_list(f_all_dic, all_num)
    else:
        name_list_all = []
    # print("*" * 10, f_all_dic, all_num)

    print("开始已修复数据处理")
    sr_fixed = []
    for i in fixed_list:
        sr_cur_fixed = jira.search_all_issue(i)
        sr_fixed.extend(sr_cur_fixed)
    sr_curr_report_fixed = [get_curr_report(i) for i in sr_fixed]
    j = 0
    for i in range(len(sr_curr_report_fixed)):
        if sr_curr_report_fixed[j] == 'remove':
            sr_curr_report_fixed.pop(j)
        else:
            j += 1

    print("开始未修复数据处理")
    sr_to_fix = []
    for i in to_fix_list:
        sr_cur_to_fix = jira.search_all_issue(i)
        sr_to_fix.extend(sr_cur_to_fix)
    # print("*" * 10, len(sr_to_fix), sr_to_fix)
    sr_to_fix_b4_17 = [get_to_fix_b4_17(i) for i in sr_to_fix]
    # print("-" * 10, len(sr_to_fix_b4_17), sr_to_fix_b4_17)
    j = 0
    for i in range(len(sr_to_fix_b4_17)):
        if sr_to_fix_b4_17[j] == 'remove':
            sr_to_fix_b4_17.pop(j)
        else:
            j += 1
    # print("=" * 10, len(sr_to_fix_b4_17), sr_to_fix_b4_17)
    sr_list_to_fix = [to_fix_issue_to_dic(i) for i in sr_to_fix_b4_17]
    # 构造这样的数据[{"lhq":"P1(严重)"},{"lhq":"P1(严重)"}]
    sum_list_to_fix = []
    for i in sr_list_to_fix:
        sum_dic_to_fix = {i["name"]: i["priority"]}
        sum_list_to_fix.append(sum_dic_to_fix)
    name_dic_to_fix = format_list(sum_list_to_fix)
    # 按域待日清
    if name_dic_to_fix:
        f_to_fix_dic, to_fix_num = name_to_region_list(name_dic_to_fix)
        name_list_to_fix_region = to_fix_region_to_list(f_to_fix_dic, to_fix_num)
    else:
        name_list_to_fix_region = []
    # print("*+" * 10, name_list_to_fix_region)
    # 按人待日清
    if name_dic_to_fix:
        name_list_to_fix = name_to_list(name_dic_to_fix)
    else:
        name_list_to_fix = []

    print("开始待确认数据处理")
    sr_to_check = []
    for i in to_check_list:
        sr_to_check_tmp = jira.search_all_issue(i)
        sr_to_check.extend(sr_to_check_tmp)
    sr_list_to_check = [to_fix_issue_to_dic(i) for i in sr_to_check]
    # 构造这样的数据[{"lhq":"P1(严重)"},{"lhq":"P1(严重)"}]
    sum_list_to_check = []
    for i in sr_list_to_check:
        sum_dic_to_check = {i["name"]: i["priority"]}
        sum_list_to_check.append(sum_dic_to_check)
    name_dic_to_check = format_list(sum_list_to_check)
    if name_dic_to_check:
        f_to_check_dic = name_to_region_list(name_dic_to_check)
        name_list_to_check = to_check_to_list(f_to_check_dic)
    else:
        name_list_to_check = []

    data = [
        "🐛**截止当前累积提交缺陷数: <font color='red'>{}</font>**".format(
            len(sr_all)),
        "\n✔**累积已修复缺陷数: <font color='green'>{}</font>, 占全部缺陷<font color='green'>{:.2%}</font>**".format(
            len(sr_fixed),
            len(
                sr_fixed) / len(
                sr_all)),
        "\n❌**累积未修复缺陷数: <font color='red'>{}</font>, 占全部缺陷<font color='red'>{:.2%}</font> (其中待日清数：<font color='red'>{}</font>, 占全部缺陷<font color='red'>{:.2%}</font>)**".format(
            len(sr_to_fix),
            len(
                sr_to_fix) / len(
                sr_all), len(sr_to_fix_b4_17),
            len(
                sr_to_fix_b4_17) / len(
                sr_all)),
        "\n❓**待确认缺陷数: <font color='grey'>{}</font>, 占全部缺陷<font color='grey'>{:.2%}</font>**".format(
            len(sr_to_check),
            len(
                sr_to_check) / len(
                sr_all))
    ]
    if len(sr_curr_report) == 0:
        data.extend([
            "\n🐛**今日提报缺陷数: <font color='red'>0</font>, 今日提报且今日修复缺陷数: <font color='green'>0</font>(当日修复比<font color='green'>0.00%</font>)**"])
    else:
        data.extend([
            "\n🐛**今日提报缺陷数: <font color='red'>{}</font>, 今日提报且今日修复缺陷数: <font color='green'>{}</font>(当日修复比<font color='green'>{:.2%}</font>)**".format(
                len(sr_curr_report), len(sr_curr_report_fixed),
                len(
                    sr_curr_report_fixed) / len(
                    sr_curr_report))])

    data.extend([f"\n\n🚩**各领域累积缺陷分布:**"])
    data.extend(name_list_all)
    data.extend([f"\n\n🚩**当前待确认缺陷:**"])
    data.extend(name_list_to_check)
    data.extend([f"\n\n🚩**待日清缺陷领域分布:**"])
    data.extend(name_list_to_fix_region)
    data.extend([f"\n\n🚩**待日清缺陷个人分布:**"])
    data.extend(name_list_to_fix)

    print(data)
    text = ''.join(data)
    print("*" * 10, text)

    # for token, secret in groups:
    #     ding.send_message(token, secret, msgtype='markdown', title='今日缺陷修复情况', text=text)

    # for token, requirement, date, reference in groups:
    #     lark.send_message(token, requirement, date, text, reference)


if __name__ == '__main__':
    main()
