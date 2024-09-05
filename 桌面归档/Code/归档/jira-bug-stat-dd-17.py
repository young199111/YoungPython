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


def issue_to_str(issue):
    return f'- {issue.key}|{issue.fields.summary}|优先级: {issue.fields.priority.name}|开发: {issue.fields.customfield_11109.displayName}'


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
        ('eb32f6520b0e88fa577b54b32a63073f6aa03dd33c8ad8bd431731bf97204a17', 'SECcb0549f9e966f222d1ada9d9415ace7c1eba4b04c83282821c2032bffa65ce3b')
    ]

    ding = DingTalk(ding_url)

    jira = MyJira(jira_url, username, password)

    current_day_fixed = 'issuetype = "缺陷(Bug)" AND status in ("[Bug]待回归", "[Bug]正常关闭") AND updated >= -17h ORDER BY reporter ASC, status DESC, created DESC'
    current_day_to_fix = 'issuetype = "缺陷(Bug)" AND status = "[BUG]待修复" AND created >= -25h AND created <= -1h ORDER BY key ASC, reporter ASC, status DESC, created DESC'

    sr_cur_fixed = jira.search_all_issue(current_day_fixed)
    sr_cur_to_fix = jira.search_all_issue(current_day_to_fix) 

    sr_list = [issue_to_str(i) for i in sr_cur_to_fix]

    data = [
        f"## **今天已修复缺陷数: {len(sr_cur_fixed)}**",
        f"## **截止现在未修复缺陷数: {len(sr_cur_to_fix)}**",
        f"### **(昨日16:00-今日16:00)**",
        f"### 未修复详情如下:"
    ]
    data.extend(sr_list)
    text = '\n'.join(data)

    for token, secret in groups:
        ding.send_message(token, secret, msgtype='markdown', title='今日缺陷修复情况', text=text)

if __name__ == '__main__':
    main()