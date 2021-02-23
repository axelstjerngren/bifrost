from os import pathsep
import tvm
from tvm import relay
from tvm.contrib import graph_runtime as runtime

# Import this add stonne as an x86 co-processor
import bifrost
from bifrost.stonne.simulator import architecture
from bifrost.runner.run import run_torch_stonne


architecture.ms_size = 128
architecture.dn_bw=64
architecture.rn_bw=64
architecture.create_config_file()


conv_paths = [
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/performance/conv_1.txt",
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/performance/conv_2.txt",
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/performance/conv_3.txt",
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/performance/conv_4.txt",
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/performance/conv_5.txt"
]
fc_paths = [
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/opt/fc_1.txt",
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/opt/fc_2.txt",
    "/Users/axelstjerngren/uni/Year4/ProjectLevel4/level-4-project/benchmarks/alexnet/tiles/opt/fc_3.txt", 
]
architecture.load_tile_config(
    conv_cfg_paths = conv_paths,
    fc_cfg_paths = fc_paths
    )

# Download an example image from the pytorch website
import urllib
from PIL import Image
from torchvision import transforms
import torch


url, filename = ("https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg", "dog.jpg")
try: urllib.URLopener().retrieve(url, filename)
except: urllib.request.urlretrieve(url, filename)

input_image = Image.open(filename)
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])
input_tensor = preprocess(input_image)
input_batch = input_tensor.unsqueeze(0) # create a mini-batch as expected by the model

from alexnet import alex_model
import time 
start = time.time()

run_torch_stonne(alex_model, input_batch)

end = time.time()
print(end - start)