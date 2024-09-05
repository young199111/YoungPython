#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import sys
import requests
import time
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


class FeiShuApi:
    def __init__(self, app_id, app_secret, user_phone):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_phone = user_phone
        self.access_token = self.get_access_token()
        self.headers = {
            "Authorization": "Bearer {}".format(self.access_token),
            "Content-Type": "application/json"
        }

    # 获取token
    def get_access_token(self):
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        try:
            res = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/", json=data)
            if res.status_code == 200:
                res_json = res.json()
                access_token = res_json.get("tenant_access_token")
                return access_token
        except Exception as e:
            return {"error": e}

    # 基于手机号获取open_id
    def get_open_id_by_phone(self):
        data = {"mobiles": [self.user_phone]}
        try:
            res = requests.post("https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id", headers=self.headers,
                                json=data)
            if res.status_code == 200:
                res_json = res.json()
                data = res_json.get("data")
                user_list = data.get("user_list")
                for i in user_list:
                    if i.get("mobile") == self.user_phone:
                        return i
        except Exception as e:
            return {"error": e}

    def send_msg_with_open_id(self, name_str, title_str, date_str, bug_str, text_str, msg_int):
        res = self.get_open_id_by_phone()
        open_id = res.get("user_id")
        if msg_int == 1:
            bool_flag = True
            msgContent = {
                "config": {
                    "wide_screen_mode": bool_flag
                },
                "header": {
                    "template": "red",
                    "title": {
                        "content": title_str,
                        "tag": "plain_text"
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": bool_flag,
                                "text": {
                                    "content": date_str,
                                    "tag": "lark_md"
                                }
                            },
                            {
                                "is_short": bool_flag,
                                "text": {
                                    "content": bug_str,
                                    "tag": "lark_md"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "div",
                        "text": {
                            "content": text_str,
                            "tag": "lark_md"
                        }
                    }
                ]
            }
            data = {
                "receive_id": open_id,
                "msg_type": "interactive",
                "content": json.dumps(msgContent)
            }
        else:
            msgContent = {"text": name_str + text_str}
            data = {
                "receive_id": open_id,
                "msg_type": "text",
                "content": json.dumps(msgContent)
            }

        try:
            res = requests.post("https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
                                headers=self.headers, json=data)
            return res.json()
        except Exception as e:
            return {"error": e}


def get_to_fix_in_xm(issue, xmin):
    issue_date = pd.to_datetime(issue.fields.created)
    now_date = pd.to_datetime(datetime.datetime.now())
    issue_date_xm = (issue_date + datetime.timedelta(minutes=xmin)).strftime("%Y-%m-%d %H:%M:%S")
    now_date_fm = now_date.strftime("%Y-%m-%d %H:%M:%S")
    if issue_date_xm > now_date_fm:
        return issue
    else:
        return 'remove'


def to_fix_issue_to_dic(issue):
    return {"name": issue.fields.assignee.displayName,
            "key": issue.key}


def format_list(_list):
    # 构造这样的数据{"lhq":{total:100,P1(严重):80, P2(一般):20},"zl":{total:152,passed:136}}
    sum_dic2 = {}
    sum_list1 = _list
    for dic1 in sum_list1:
        for name1 in dic1:
            if name1 not in sum_dic2:  # hzy不在sum_dic2这个里面
                sum_dic2[name1] = {"total": 1, "keys": (dic1[name1],)}
            else:  # hzy在sum_dic2这个里面
                sum_dic2[name1]["total"] += 1
                sum_dic2[name1]["keys"] += (dic1[name1],)
    sum_dic2 = dict(sorted(sum_dic2.items(), key=lambda n: int(n[1]['total']), reverse=True))
    return sum_dic2


def name_to_phone_list(_dic):
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
                   'keys': _dic[i]['keys']}
        tmp_list.append(tmp_dic)
    df = pd.DataFrame(tmp_list)
    # print(df)
    df['手机'] = df.apply(set_department, args=(df_user, '责任人', '手机'), axis=1)
    print(df)
    f_list = df.apply(lambda x: tuple(x), axis=1).values.tolist()
    return f_list


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


def main():
    jira_url = 'https://jira.znlhzl.org'
    username = 'scrummaster'
    password = 'znlh1234'

    # 测试版本
    # app_id = "cli_a3044003803c100e"
    # app_secret = "kyLRVFmGar24RLgwxqqOzccjbjnTZSSi"

    # 正式版本
    app_id = "cli_a304284ddb38100e"
    app_secret = "s8Plxyo4tulw9yxc6s0VedSjHJsNRUhg"

    xmin = int(sys.argv[1])
    print("xmin is: ", xmin)
    title_str = "🐛【提醒】过去{}分钟内名下新增待处理BUG".format(xmin)
    date_str = '**时间：**\n' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    base_text = ["点击下方链接直接进入相关Bug单：\n"]

    jira = MyJira(jira_url, username, password)

    to_fix_list = [
        'project = PLA2 AND issuetype = "缺陷(Bug)" AND status = "[BUG]待修复" AND created >= 2022-12-12'
    ]

    print("开始未修复数据处理")
    sr_to_fix = []
    for i in to_fix_list:
        sr_cur_to_fix = jira.search_all_issue(i)
        sr_to_fix.extend(sr_cur_to_fix)
    sr_to_fix_in_xm = [get_to_fix_in_xm(i, xmin) for i in sr_to_fix]
    j = 0
    for i in range(len(sr_to_fix_in_xm)):
        if sr_to_fix_in_xm[j] == 'remove':
            sr_to_fix_in_xm.pop(j)
        else:
            j += 1
    sr_list_to_fix = [to_fix_issue_to_dic(i) for i in sr_to_fix_in_xm]
    # 构造这样的数据[{"lhq":"P1(严重)"},{"lhq":"P1(严重)"}]
    sum_list_to_fix = []
    for i in sr_list_to_fix:
        sum_dic_to_fix = {i["name"]: i["key"]}
        sum_list_to_fix.append(sum_dic_to_fix)
    name_dic_to_fix = format_list(sum_list_to_fix)
    # 按域待日清
    if name_dic_to_fix:
        f_to_fix_list = name_to_phone_list(name_dic_to_fix)
    else:
        f_to_fix_list = []

    if f_to_fix_list:
        for i in f_to_fix_list:
            name_str = i[0]
            bug_str = "**新增Bug数：\n<font color='red'>{}</font>**".format(i[1])

            if i[3] == "未知":
                text_str = "的手机号信息未配置"
                msg_int = 2
                user_phone = "13770996232"
                fei = FeiShuApi(app_id, app_secret, user_phone)
                res = fei.send_msg_with_open_id(name_str, title_str, date_str, bug_str, text_str, msg_int)
                print(res)
            else:
                add_text = []
                for j in i[2]:
                    temp_str = "🚩  [{}](https://jira.znlhzl.org/browse/{})\n".format(j, j)
                    add_text.append(temp_str)
                base_text.extend(add_text)
                text_str = ''.join(base_text)
                msg_int = 1
                user_phone = str(i[3])
                fei = FeiShuApi(app_id, app_secret, user_phone)
                res = fei.send_msg_with_open_id(name_str, title_str, date_str, bug_str, text_str, msg_int)
                print(res)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
