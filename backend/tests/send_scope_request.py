#!/usr/bin/env python3
import requests, json
query='file tuần trước tôi up lên có lệ phí dăng kí là bao nhiêu đi bạn'
headers={'Authorization':'Bearer oMSHHGeNtc7NLBg3Bh1cgPWqCbDlG3ki5BATdCYT7eI'}
payload={'question':query,'scope':'system'}
print('Sending system-scope query...')
r=requests.post('http://127.0.0.1:8000/chat',json=payload,headers=headers)
print(r.status_code)
print(json.dumps(r.json(),ensure_ascii=False,indent=2))
