#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@文件    : test3.py
@说明    : 
@时间    : 2022/12/8 10:55
@作者    : Young
@版本    : 1.0 
"""
import sys
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
                   'keys': _dic[i]['keys']}
        tmp_list.append(tmp_dic)
    df = pd.DataFrame(tmp_list)
    # print(df)
    df['手机'] = df.apply(set_department, args=(df_user, '责任人', '手机'), axis=1)
    print(df)
    df_merge = df['total'].groupby(df['手机']).sum()
    # print(df_merge)
    f_dic = dict(df_merge)
    f_dic = dict(sorted(f_dic.items(), key=lambda n: int(n[1]), reverse=True))
    # print(f_dic)
    return f_dic, df['total'].sum()


def to_fix_region_to_list(_dic, _num):
    all_list = []
    for i, j in enumerate(_dic):
        temp_str = "\n&#62; **<font color='grey'>{}</font>** |待日清缺陷总数：**<font color='red'>{}</font>** |占比：**<font color='red'>{:.2%}</font>**".format(
            j, _dic[j], _dic[j] / _num)
        all_list.append(temp_str)
    return all_list


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
    lark_url = 'https://open.feishu.cn/open-apis/bot/v2/hook/'

    req_name = "呼叫1.1（1129）"
    date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    groups = [
        ('75a2b3a3-45d7-46ca-b99b-23d99d95bf54', '**需求**\n' + req_name, '**时间**\n' + date_time,
         '[数据来源Jira](https://jira.znlhzl.org/)')
    ]

    jira = MyJira(jira_url, username, password)

    to_fix_list = [
        'issuetype = "缺陷(Bug)" AND status in ("[BUG]待修复") AND text ~ 【线索培育】 AND created >= 2022-11-01 AND reporter in (lulan, shijiaqi, lijingjing, yanmin, zhanglin1, geyaru, wangweina, wangweina2, wangyang7) ORDER BY status ASC, cf[11109] DESC, assignee ASC'
    ]

    print("开始未修复数据处理")
    sr_to_fix = []
    for i in to_fix_list:
        sr_cur_to_fix = jira.search_all_issue(i)
        sr_to_fix.extend(sr_cur_to_fix)
    # print("*" * 10, len(sr_to_fix), sr_to_fix)
    sr_to_fix_in_5m = [get_to_fix_in_xm(i, 2000) for i in sr_to_fix]
    # print("-" * 10, len(sr_to_fix_in_5m), sr_to_fix_in_5m)
    j = 0
    for i in range(len(sr_to_fix_in_5m)):
        if sr_to_fix_in_5m[j] == 'remove':
            sr_to_fix_in_5m.pop(j)
        else:
            j += 1
    print("=" * 10, len(sr_to_fix_in_5m), sr_to_fix_in_5m)
    sr_list_to_fix = [to_fix_issue_to_dic(i) for i in sr_to_fix_in_5m]
    # 构造这样的数据[{"lhq":"P1(严重)"},{"lhq":"P1(严重)"}]
    sum_list_to_fix = []
    for i in sr_list_to_fix:
        sum_dic_to_fix = {i["name"]: i["key"]}
        sum_list_to_fix.append(sum_dic_to_fix)
    print("=" * 10, len(sum_list_to_fix), sum_list_to_fix)
    name_dic_to_fix = format_list(sum_list_to_fix)
    print("=" * 10, len(name_dic_to_fix), name_dic_to_fix)
    # 按域待日清
    if name_dic_to_fix:
        f_to_fix_dic, to_fix_num = name_to_region_list(name_dic_to_fix)
        name_list_to_fix_region = to_fix_region_to_list(f_to_fix_dic, to_fix_num)
    else:
        name_list_to_fix_region = []
    print("*+" * 10, name_list_to_fix_region)

    data = [
        "\n❌**累积未修复缺陷数: <font color='red'>{}</font>, 占全部缺陷<font color='red'>{:.2%}</font> (其中待日清数：<font color='red'>{}</font>, 占全部缺陷<font color='red'>{:.2%}</font>)**".format(
            len(sr_to_fix),
            len(
                sr_to_fix) / 100, len(sr_to_fix_in_5m),
            len(
                sr_to_fix_in_5m) / 100)
    ]

    data.extend([f"\n\n🚩**待日清缺陷领域分布:**"])
    data.extend(name_list_to_fix_region)

    print(data)
    text = ''.join(data)
    print("*" * 10, text)

    # for token, secret in groups:
    #     ding.send_message(token, secret, msgtype='markdown', title='今日缺陷修复情况', text=text)

    # for token, requirement, date, reference in groups:
    #     lark.send_message(token, requirement, date, text, reference)


if __name__ == '__main__':
    main()
