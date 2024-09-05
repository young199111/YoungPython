#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@文件    : test.py
@说明    : 
@时间    : 2022/12/6 15:33
@作者    : Young
@版本    : 1.0 
"""

import requests
import json


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

    def send_msg_with_open_id(self, date_str, bug_str, text_str):
        res = self.get_open_id_by_phone()
        open_id = res.get("user_id")

        bool_flag = True
        msgContent = {
            "config": {
                "wide_screen_mode": bool_flag
            },
            "header": {
                "template": "red",
                "title": {
                    "content": "🐛【提醒】过去5分钟内名下新增待处理BUG",
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

        try:
            res = requests.post("https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
                                headers=self.headers, json=data)
            return res.json()
        except Exception as e:
            return {"error": e}


if __name__ == '__main__':
    app_id = ""
    app_secret = ""
    user_phone = ""
    fei = FeiShuApi(app_id, app_secret, user_phone)
    res = fei.send_msg_with_open_id("Testing message")
    print(res)
