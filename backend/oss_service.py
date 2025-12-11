#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云 OSS 服务
"""

import os
import oss2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class OSSService:
    def __init__(self):
        # 从环境变量读取配置
        access_key_id = os.getenv('OSS_ACCESS_KEY_ID')
        access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
        endpoint = os.getenv('OSS_ENDPOINT')
        bucket_name = os.getenv('OSS_BUCKET_NAME')
        
        if not all([access_key_id, access_key_secret, endpoint, bucket_name]):
            raise ValueError("OSS配置不完整，请检查 backend/.env 文件中的配置")
        
        auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name)
        self.json_prefix = os.getenv('OSS_JSON_PREFIX', 'qq-reports/json/')
        self.result_prefix = os.getenv('OSS_RESULT_PREFIX', 'qq-reports/results/')
    
    def upload_json(self, file_path, original_filename):
        """上传JSON文件到OSS"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 生成唯一的文件名
        file_ext = os.path.splitext(original_filename)[1]
        oss_key = f"{self.json_prefix}{timestamp}_{original_filename}"
        
        try:
            with open(file_path, 'rb') as f:
                self.bucket.put_object(oss_key, f)
            return oss_key
        except Exception as e:
            raise Exception(f"上传JSON到OSS失败: {str(e)}")
    
    def download_json(self, oss_key, local_path):
        """从OSS下载JSON文件"""
        try:
            self.bucket.get_object_to_file(oss_key, local_path)
            return True
        except Exception as e:
            raise Exception(f"从OSS下载JSON失败: {str(e)}")
    
    def upload_result_html(self, file_path, report_id):
        """上传结果HTML到OSS"""
        oss_key = f"{self.result_prefix}{report_id}.html"
        try:
            with open(file_path, 'rb') as f:
                self.bucket.put_object(oss_key, f)
            return oss_key
        except Exception as e:
            raise Exception(f"上传结果HTML到OSS失败: {str(e)}")
    
    def get_file_url(self, oss_key, expires=3600):
        """获取文件的签名URL"""
        try:
            return self.bucket.sign_url('GET', oss_key, expires)
        except Exception as e:
            raise Exception(f"生成文件URL失败: {str(e)}")
    
    def delete_file(self, oss_key):
        """删除OSS文件"""
        try:
            self.bucket.delete_object(oss_key)
            return True
        except Exception as e:
            raise Exception(f"删除OSS文件失败: {str(e)}")
    
    def generate_upload_signature(self, filename):
        """
        生成OSS上传签名，供前端直接上传使用
        返回：上传所需的所有信息
        """
        from oss2.models import POLICY_PERMISSIONS
        import json
        import base64
        import hmac
        import hashlib
        from datetime import datetime, timedelta
        
        # 生成唯一的文件key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_ext = os.path.splitext(filename)[1]
        oss_key = f"{self.json_prefix}{timestamp}_{filename}"
        
        # 设置上传策略（1小时有效期）
        expire_time = datetime.utcnow() + timedelta(hours=1)
        expire_timestamp = int(expire_time.timestamp())
        
        # 构建policy
        policy_dict = {
            "expiration": expire_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "conditions": [
                ["content-length-range", 0, 100 * 1024 * 1024],  # 最大100MB
                ["eq", "$key", oss_key]
            ]
        }
        
        policy_str = json.dumps(policy_dict)
        policy_base64 = base64.b64encode(policy_str.encode()).decode()
        
        # 计算签名
        access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET')
        signature = base64.b64encode(
            hmac.new(
                access_key_secret.encode(),
                policy_base64.encode(),
                hashlib.sha1
            ).digest()
        ).decode()
        
        # 返回上传所需信息
        return {
            "access_key_id": os.getenv('OSS_ACCESS_KEY_ID'),
            "policy": policy_base64,
            "signature": signature,
            "key": oss_key,
            "host": f"https://{self.bucket.bucket_name}.{os.getenv('OSS_ENDPOINT')}",
            "expire": expire_timestamp
        }
