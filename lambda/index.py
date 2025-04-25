# lambda/index.py
import json
import urllib.request
import urllib.error
import re

# FastAPI 側のエンドポイント URL（ngrok公開アドレス）
FASTAPI_URL = "https://cc9b-35-245-188-248.ngrok-free.app/generate"

def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Lambda テストイベント vs API Gateway
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        message = body['message'] if 'message' in body else body.get('prompt', '')
        conversation_history = body.get('conversationHistory', [])
        
        # FastAPI に渡す prompt は最新の user メッセージのみ使用（単一プロンプト）
        prompt = message
        
        # FastAPI 用の JSON ペイロード
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True
        }
        
        # HTTP POSTリクエストを送信（urllibを使用）
        req = urllib.request.Request(
            FASTAPI_URL,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=60) as response:
            response_body = response.read().decode("utf-8")
            result = json.loads(response_body)

        print("FastAPI response:", json.dumps(result, ensure_ascii=False))

        # FastAPI からの応答を取り出す
        assistant_response = result.get("generated_text", "")
        
        # 会話履歴にアシスタント応答を追加
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": assistant_response})

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except urllib.error.HTTPError as e:
        error_message = e.read().decode()
        print("HTTPError:", e.code, error_message)
        return {
            "statusCode": e.code,
            "body": json.dumps({
                "success": False,
                "error": error_message
            })
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
