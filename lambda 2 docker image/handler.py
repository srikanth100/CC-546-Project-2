import json
import boto3
import base64
import numpy as np
import torch
import traceback
import torch.nn.functional as F
import torchvision.transforms as transforms
from torch import nn
from PIL import Image
from torch.nn.init import *
from boto3.dynamodb.conditions import Key
from models.inception_resnet_v1 import InceptionResnetV1

lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1', 
                            endpoint_url='https://dynamodb.us-east-1.amazonaws.com')
DYNAMO_TABLE_NAME = 'student'
table = dynamodb.Table(DYNAMO_TABLE_NAME)

class Flatten(nn.Module):
    def __init__(self):
        super(Flatten, self).__init__()
        
    def forward(self, x):
        x = x.view(x.size(0), -1)
        return x

class normalize(nn.Module):
    def __init__(self):
        super(normalize, self).__init__()
        
    def forward(self, x):
        x = F.normalize(x, p=2, dim=1)
        return x

def build_model(num_classes):
	print("Starting build model !!")
	model_ft = InceptionResnetV1(pretrained='vggface2', classify=False, num_classes=num_classes)
	last_conv_block = list(model_ft.children())[-6:]
	# print(last_conv_block)

    # Remove the last layers after conv block and place in layer_list .
	layer_list = list(model_ft.children())[-5:] # all final layers
    # print(f"layer_list: {layer_list}")

    # Put all beginning layers in an nn.Sequential . model_ft is now a torch model but without the final linear, pooling, batchnorm, and sigmoid layers.
	model_ft = nn.Sequential(*list(model_ft.children())[:-5])
	for param in model_ft.parameters():
		param.requires_grad = False

    # Then you can apply the final layers back to the new Sequential model.
	model_ft.avgpool_1a = nn.AdaptiveAvgPool2d(output_size=1)
	model_ft.last_linear = nn.Sequential(
        Flatten(),
        nn.Linear(in_features=1792, out_features=512, bias=False),
        normalize()
    )
    # model_ft.logits = nn.Linear(layer_list[3].in_features, len(class_names))
	model_ft.logits = nn.Linear(512, num_classes)
	model_ft.softmax = nn.Softmax(dim=1)
	print("Ending build model !!")
	return model_ft

def face_recognition_handler(event, context):
	try:
		image_name = event['key']
		enc_string = event['imageEncoded']
		the_file = base64.b64decode(enc_string.encode('utf-8'))
		image_path = "/tmp/" + image_name
		with open(image_path, "wb") as fh:
			fh.write(the_file)
		labels_dir = "./checkpoint/labels.json"
		model_path = "./checkpoint/model_vggface2_best.pth"
		# read labels
		with open(labels_dir) as f:
			labels = json.load(f)
		print(f"labels: {labels}")
		device = torch.device('cpu')
		model = build_model(len(labels)).to(device)
		model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'))['model'])
		model.eval()
		print(f"Best accuracy of the loaded model: {torch.load(model_path, map_location=torch.device('cpu'))['best_loss']}")
		img = Image.open(image_path)
		img_tensor = transforms.ToTensor()(img).unsqueeze_(0).to(device)
		outputs = model(img_tensor)
		_, predicted = torch.max(outputs.data, 1)
		result = labels[np.array(predicted.cpu())[0]]
		img_name = image_path.split("/")[-1]
		img_and_result = f"({img_name}, {result})"
		print(f"Image and its recognition result is: {img_and_result}")
		print("The resulting classification is: ", result, " for file: ", img_name)
		response = table.query(KeyConditionExpression=Key('name').eq(result))
		print("The response is : ", response)
		print("The result is : ", result)
		return response['Items'][0]
	except Exception as e:
		print("Error occured: {}".format(e))
		print("Stack Trace: {}", traceback.format_exc())
