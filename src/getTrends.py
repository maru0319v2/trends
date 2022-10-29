import datetime

from requests_oauthlib import OAuth1
import requests
import pprint
from boto3.session import Session
import config


def lambda_handler(event, context):
    # トレンドを取得する
    trends_dict = get_trend()
    # DynamoDB情報取得
    dynamo_table = get_dynamo_table()
    # DynamoDBへ書き込み
    insert_data_from_json(dynamo_table, trends_dict)


# トレンドを取得する
def get_trend():
    # 認証しレスポンス取得
    response = requests.get("https://api.twitter.com/1.1/trends/place.json?id=23424856", auth=OAuth1(config.CK, config.CKS, config.AT, config.ATS))
    dicts = response.json()[0]['trends']

    # 現在時刻の取得(JST)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9), 'JST'))
    date = now.strftime("%Y%m%d")
    time = now.strftime("%H%M")

    # トレンドデータを整形
    for cnt in range(0, 50):
        count = cnt + 1
        dicts[cnt]["date"] = int(date)
        dicts[cnt]["timeRank"] = time + "_" + str(count)
        dicts[cnt]["value"] = dicts[cnt]["name"]
        # 不要な要素を削除
        del dicts[cnt]["url"], dicts[cnt]["promoted_content"], \
            dicts[cnt]["query"], dicts[cnt]["tweet_volume"], \
            dicts[cnt]["name"]

    # トレンド取得結果を表示
    pprint.pprint(dicts[0:50])
    print('Successfully got Trends from TwitterAPI.')
    return dicts


# DynamoDBの情報を取得
def get_dynamo_table():
    session = Session(
        aws_access_key_id=config.AAK,
        aws_secret_access_key=config.AAS,
        region_name=config.REGION_NAME
    )

    dynamodb = session.resource('dynamodb')
    dynamo_table = dynamodb.Table('trendsData')
    return dynamo_table


# DynamoDBへ書き込み
def insert_data_from_json(table, trends_dict):
    with table.batch_writer() as batch:
        for record in trends_dict:
            batch.put_item({k: v for k, v in record.items()})
    print('Successfully inserted Trends into DynamoDB.')
