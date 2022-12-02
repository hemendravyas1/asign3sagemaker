import json
import os
import io
import boto3
import email
import string
import sys
import numpy as np
from hashlib import md5
import ast

#ENDPOINT = os.environ['sms-spam-classifier-mxnet-2022-11-21-22-11-36-632']
ENDPOINT = 'sms-spam-classifier-mxnet-2022-11-21-22-11-36-632'
runtime = boto3.Session().client(service_name='sagemaker-runtime',region_name='us-east-1')
#bytes_to_read = 512
s3_client = boto3.client('s3')

if sys.version_info < (3,):
    maketrans = string.maketrans
else:
    maketrans = str.maketrans

def vectorize_sequences(sequences, vocabulary_length):
    results = np.zeros((len(sequences), vocabulary_length))
    for i, sequence in enumerate(sequences):
       results[i, sequence] = 1.
    return results

def one_hot_encode(messages, vocabulary_length):
    data = []
    for msg in messages:
        temp = one_hot(msg, vocabulary_length)
        data.append(temp)
    return data

def text_to_word_sequence(text,
                          filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
                          lower=True, split=" "):
    if lower:
        text = text.lower()

    if sys.version_info < (3,):
        if isinstance(text, unicode):
            translate_map = dict((ord(c), unicode(split)) for c in filters)
            text = text.translate(translate_map)
        elif len(split) == 1:
            translate_map = maketrans(filters, split * len(filters))
            text = text.translate(translate_map)
        else:
            for c in filters:
                text = text.replace(c, split)
    else:
        translate_dict = dict((c, split) for c in filters)
        translate_map = maketrans(translate_dict)
        text = text.translate(translate_map)

    seq = text.split(split)
    return [i for i in seq if i]

def one_hot(text, n,
            filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
            lower=True,
            split=' '):
    return hashing_trick(text, n,
                         hash_function='md5',
                         filters=filters,
                         lower=lower,
                         split=split)


def hashing_trick(text, n,
                  hash_function=None,
                  filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
                  lower=True,
                  split=' '):
    if hash_function is None:
        hash_function = hash
    elif hash_function == 'md5':
        hash_function = lambda w: int(md5(w.encode()).hexdigest(), 16)

    seq = text_to_word_sequence(text,
                                filters=filters,
                                lower=lower,
                                split=split)
    return [int(hash_function(w) % (n - 1) + 1) for w in seq]

# ENDPOINT = 'sms-spam-classifier-mxnet-2022-05-03-02-58-36-591'
# SENDER = "hsapte99@gmail.com"
# SENDER = 'hello@apteharsh.ml'
# SENDER = str(toEmailId)

def reply(receive_date, subject, body, classfication, conf_score, recipientEmailAddress, toEmailId):
    client = boto3.client('ses')
    SUBJECT = "SPAM Identification"
    BODY_TEXT = ("This email was sent with Amazon SES using the AWS SDK for Python (Boto).")
    BODY_HTML = """<html>
                    <head></head>
                    <body>
                      <p>
                        """+"Hello! <br>\
                        <br>We received your email sent at {} with the subject - '<b>{}</b>'. <br> \
                        <br>Here is a 240 character sample of the email body: <br> <i>{}</i> <br>\
                        <br>The email was categorized as <mark><b>{}</b></mark> with a <b>{}%</b> confidence."\
                        .format(receive_date, subject, body, classfication, conf_score)+"""
                      </p>
                    </body>
                    </html>
                """
    CHARSET = "UTF-8"
    message = "We received your email sent at {} with the subject {}. \n Here is a 240 character sample of the email body:\
    <b>{}</b>. \n The email was categorized as {} with a {}% confidence. This is MESSAGE of mail".format(receive_date, subject, body, classfication, conf_score)
    response = client.send_email(
        Destination={
            'ToAddresses': [
                recipientEmailAddress
            ],
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': BODY_HTML,
                },
                'Text': {
                    'Charset': CHARSET,
                    'Data': message,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': SUBJECT,
            },
        },
        Source=toEmailId)
    print(response)

def lambda_handler(event, context):
    print("This is running")
    print(event)
    key = event['Records'][0]['s3']['object']['key']
    s3 = boto3.resource('s3')
    obj = s3.Object('sages3hem',key)
    print(key)
    msg = email.message_from_bytes(obj.get()['Body'].read())
    #msg='ahsdfjsh'
    #it works response = s3_client.get_object(Bucket='sages3hem', Key=key)
    #it works msg = response['Body'].read()
    print(msg)
    #msg1[] = msg.decode("utf-8")
    #print(msg1)
    #msg1 = ast.literal_eval(msg)
    #print(msg1)
    #msg = s3.Object(s3, key).get()['Body'].read(bytes_to_read)
    #a = json.loads(msg)
    #print(a['From'])
    #msg1=msg.json()
    #print(msg1)
    print('==========================================')
    #for ms in msg1:
    #    print(ms)

    recipientEmailAddress = msg['From']
    toEmailId = msg['To']
    receive_date = msg['date']
    subject = msg['subject']

    if msg.is_multipart():
        for part in msg.get_payload():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload()
    else:
        body = msg.get_payload()

    body = [body.strip()]

    print(recipientEmailAddress, receive_date, subject, "\n", body)
    # body = ["FreeMsg: Txt: CALL to No: 86888 & claim your reward of 3 hours talk time to use from your phone now! ubscribe6GBP/ mnth inc 3hrs 16 stop?txtStop"]
    vocabulary_length = 9013
    one_hot_test_messages = one_hot_encode(body, vocabulary_length)
    encoded_test_messages = vectorize_sequences(one_hot_test_messages, vocabulary_length)


    payload = json.dumps(encoded_test_messages.tolist())
    result = runtime.invoke_endpoint(EndpointName=ENDPOINT,ContentType='application/json',Body=payload)
    print(result["Body"])
    print("hemendra1")
    response = json.loads(result["Body"].read().decode("utf-8"))
    print(response)
    print("hemendra2")
    pred = int(response.get('predicted_label')[0][0])
    if pred == 1:
        classfication = "SPAM"
    elif pred == 0:
        classfication = "NOT SPAM"
    conf_score = str(round(float(response.get('predicted_probability')[0][0]) * 100, 2))
    print(classfication)
    print("hemendra3")
    print(conf_score)
    print("hemendra4")
    body =  body[0]

    reply(receive_date, subject, body, classfication, conf_score, recipientEmailAddress, toEmailId)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
