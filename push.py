import os
import time
import boto3
import sys
import json
import threading

VIDEO_BUCKET = 'cse546-video-storage'

s3 = boto3.client('s3', region_name='us-east-1')
lambda_client = boto3.client('lambda')

def upload_file_to_s3(bucket_name, file_name):
	try:
		object_name = os.path.basename(file_name)
		s3.upload_file(file_name, bucket_name, object_name)
	except Exception as e:
		print('Error occurred: {}'.format(e))

def thread_function(file_name, num):
	start_time = time.time()
	upload_file_to_s3(VIDEO_BUCKET, file_name)
	os.remove(file_name)
	result = lambda_client.invoke(
		FunctionName='s3test',
                InvocationType='RequestResponse',
                Payload=json.dumps({'video_name' : file_name})
	)
	end_time = time.time() - start_time
	result = json.loads(result['Payload'].read().decode('utf-8'))
	print('--------------------------')
	print('The \#{} person recognized: {}, {}, {}'.format(num, result['name'],
		result['major'], result['year']))
	print('Latency: {:.2f} seconds'.format(end_time))

def push(t):
	total_time = int(120 * float(t))
	thread_list = []
	for i in range(total_time):
		file_name = 'video_' + str(i+1) + '.h264'
		try:
			cmd = 'raspivid -o ' + file_name + ' -t 500 -h 160 -w 160'
			os.system(cmd)
		except Exception as e:
			print('Error occurred: {}'.format(e))
		thread_1 = threading.Thread(target=thread_function, args=(file_name, i + 1))
		thread_list.append(thread_1)
		thread_1.start()

	for thread in enumerate(thread_list):
		thread.join()

if __name__ == '__main__':
	push(sys.argv[1])
