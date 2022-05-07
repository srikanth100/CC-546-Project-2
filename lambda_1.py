import os, json, time, boto3, botocore, base64

lambda_client = boto3.client('lambda')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    start_time = time.time()
    video_name = event['video_name']
    s3.download_file('cse546-video-storage', video_name, '/tmp/' + video_name)
    video_path = '/tmp/' + video_name
    image_name = video_name.split('.')[0] + ".png"
    image_path = '/tmp/' + image_name
    cmd = "/opt/bin/ffmpeg -i \"" + video_path + "\" -ss 00:00:00.250 -vframes 1 " + str(image_path)
    os.system(cmd)
    with open(str(image_path), 'rb') as image_file:
        encoded_string = base64.b64encode(
            image_file.read()).decode('utf-8')

    result = lambda_client.invoke(
        FunctionName='face_recognition_handle',
        InvocationType='RequestResponse',
        Payload=json.dumps({'imageEncoded': encoded_string, 'key': image_name, 'lambda1time': time.time() - start_time})
    )
    print('The result is : ', result)
    return json.loads(result['Payload'].read().decode('utf-8'))
