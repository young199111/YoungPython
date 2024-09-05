import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
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


def issue_to_dic(issue):
    return {"name": issue.fields.assignee.displayName,
            "priority": issue.fields.priority.name}


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
        f'- **<font color=#921AFF>{i}</font>** |待修复总数：**<font color=#FF0000>{_dic[i]["total"]}</font>** |P0(致命): **<font color=#F75000>{_dic[i]["P0(致命)"]}</font>** |P1(严重): **<font color=#F75000>{_dic[i]["P1(严重)"]}</font>** |P2(一般): <font color=#FF8000>{_dic[i]["P2(一般)"]}</font> |P3(轻微): <font color=#46A3FF>{_dic[i]["P3(轻微)"]}</font> |P4(建议): <font color=#46A3FF>{_dic[i]["P4(建议)"]}</font>'
        for i in _dic]
    # return [
    #     f'- {i} |待修复总数：{_dic[i]["total"]} |P0(致命): {_dic[i]["P0(致命)"]} |P1(严重): {_dic[i]["P1(严重)"]} |P2(一般): {_dic[i]["P2(一般)"]} |P3(轻微): {_dic[i]["P3(轻微)"]} |P4(建议): {_dic[i]["P4(建议)"]}'
    #     for i in _dic]


def main():
    jira_url = 'https://jira.znlhzl.org'
    username = 'scrummaster'
    password = 'znlh1234'
    ding_url = 'https://oapi.dingtalk.com/robot/send'

    # groups = [
    #     ('166d9462f45f264501c74f33ee98256e10d7a820049f76a78285e33e2bc4650f', 'SEC955f3fba19a91876c7f1fc7c111088944078b0d3bfe0c78fa2a4b07591f2f85f'),
    #     ('2f14aa46561fabb8d9148cbcbf291250489018ce64cd5475fd9379f8752ccd6a', 'SEC1ee2001656e9156758f7bde693d4d776b7d49ecdc1a64380229f552cd511d735')
    # ]
    groups = [
        # 商带客2.0
        # ('845311024627cce8dc430b8739170180399eabe240df14d10d25e2c55038b7a0',
        #  'SECbbc12afeaac36bd65681eeb9d569fe4c4f58bbd2ebd2f846c2e8c4dee89e415c')
        # 平台知识库
        # ('12b205cc2928bbb26f0dc381abe1cbcf6622f16a9ccd5aab895c82e1b6909851',
        #  'SECe2367067629c5da0cfd0626807a0d73c591c852b4e529986189cdfb8b05be6b0')
        # 客端CRM
        ('03c8ec81a22edc938cea7587668492298406f5573ea8148ebdd22ce001b56d28',
         'SEC8da1d9ded14bddad8939892c422a5d8730842800460396e0ec132b7eaeafeb14')
    ]

    ding = DingTalk(ding_url)

    jira = MyJira(jira_url, username, password)

    # 商带客2.0
    # fixed_list = [
    #     'issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND created >= 2022-06-07 AND text ~ 【商端CRM】 ORDER BY created DESC',
    #     'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ "【属地化】" AND created >= 2022-04-01 AND reporter in (wangyang7, yanmin, geyaru, lijingjing) ORDER BY status ASC',
    #     'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ 【交撮平台】 AND created >= 2022-04-01 AND reporter in (wangyang7, wumeng1, yanmin, geyaru, lijingjing) ORDER BY status ASC',
    #     'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ 【交撮平台】 AND created >= 2022-04-01 AND reporter in (luanlin, zhangcuicui, gaochen1) ORDER BY status ASC',
    #     'issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ "【商带客2.0财务侧】"'
    # ]
    # to_fix_list = [
    #     'issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND created >= 2022-06-07 AND text ~ 【商端CRM】 ORDER BY created DESC',
    #     'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND text ~ "【属地化】" AND created >= 2022-04-01 AND reporter in (wangyang7, yanmin, geyaru, lijingjing) ORDER BY status ASC',
    #     'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND text ~ 【交撮平台】 AND created >= 2022-04-01 AND reporter in (wangyang7, wumeng1, yanmin, geyaru, lijingjing) ORDER BY status ASC',
    #     'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND text ~ 【交撮平台】 AND created >= 2022-04-01 AND reporter in (luanlin, zhangcuicui, gaochen1) ORDER BY status ASC',
    #     'issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND text ~ "【商带客2.0财务侧】"'
    # ]

    # 平台知识库
    # fixed_list = ['project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ "【知识库" AND created >= 2022-04-01 AND reporter in (wangyang7, geyaru, lijingjing) ORDER BY status ASC']
    # to_fix_list = ['project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status = "[BUG]待修复" AND text ~ "【知识库" AND created >= 2022-04-01 AND reporter in (wangyang7, geyaru, lijingjing) ORDER BY status ASC']

    # 客端CRM
    fixed_list = [
        'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ 【基础 AND created >= 2022-06-28 AND reporter in (huangtaibei, songhuidou) ORDER BY priority DESC, status ASC',
        'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ 【交易 AND created >= 2022-06-28 AND reporter in (luanlin, lulan) ORDER BY priority DESC, status ASC',
        'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND text ~ 【CRM AND created >= 2022-06-28 AND reporter in (wangyang7, yanmin, geyaru, lijingjing) ORDER BY priority DESC, status ASC'
    ]
    to_fix_list = [
        'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status = "[BUG]待修复"  AND text ~ 【基础 AND created >= 2022-06-28 AND reporter in (huangtaibei, songhuidou) ORDER BY priority DESC, status ASC',
        'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status = "[BUG]待修复"  AND text ~ 【交易 AND created >= 2022-06-28 AND reporter in (luanlin, lulan) ORDER BY priority DESC, status ASC',
        'project in (PLA2, DTC) AND issuetype = "缺陷(Bug)" AND status = "[BUG]待修复"  AND text ~ 【CRM AND created >= 2022-06-28 AND reporter in (wangyang7, yanmin, geyaru, lijingjing) ORDER BY priority DESC, status ASC'
    ]

    sr_fixed = []
    for i in fixed_list:
        sr_cur_fixed = jira.search_all_issue(i)
        sr_fixed.extend(sr_cur_fixed)

    sr_to_fix = []
    for i in to_fix_list:
        sr_cur_to_fix = jira.search_all_issue(i)
        sr_to_fix.extend(sr_cur_to_fix)

    sr_list0 = [issue_to_dic(i) for i in sr_to_fix]

    # 构造这样的数据[{"lhq":"P1(严重)"},{"lhq":"P1(严重)"}]
    sum_list1 = []
    for i in sr_list0:
        sum_dic1 = {}
        sum_dic1[i["name"]] = i["priority"]
        sum_list1.append(sum_dic1)

    name_dic = format_list(sum_list1)
    name_list = name_to_list(name_dic)
    # sr_list = [issue_to_str(i) for i in sr_to_fix]

    data = [
        f"## **截止当前已修复缺陷数: <font color=#28FF28>{len(sr_fixed)}</font>**",
        f"## **截止当前未修复缺陷数: <font color=#FF0000>{len(sr_to_fix)}</font>**",
        f"### 未修复开发明细:"
    ]
    # data = [
    #     f"## **截止当前已修复缺陷数: {len(sr_fixed)}**",
    #     f"## **截止当前未修复缺陷数: {len(sr_to_fix)}**",
    #     f"### 未修复开发明细:"
    # ]
    data.extend(name_list)
    # data.extend([f"### 未修复详情如下:"])
    # data.extend(sr_list)
    text = '\n'.join(data)
    print(text)

    # for token, secret in groups:
    #     ding.send_message(token, secret, msgtype='markdown', title='今日缺陷修复情况', text=text)


if __name__ == '__main__':
    main()
