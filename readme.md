# Bifrost

Bifrost (/ˈbɪvrɒst/) is a tool for the evaulation and optimisation of DNN accelerators. The Bifrost interface bridges [Apache TVM](https://tvm.apache.org) (a deep learning compiler) with [STONNE](https://arxiv.org/pdf/2006.07137.pdf) (a simulator for DNN accelerators). Bifrost let's you run DNN models on simulated reconfigurable DNN accelerators.

The name is taken from Norse mythology, where Bifrost is the bridge between Midgard and Asgard. 

# Quickstart Guide

## Installation
Bifrost is a Python tool. You can install it using pip:
```
pip install git+https://github.com/axelstjerngren/level-4-project#"egg=bifrost&subdirectory=bifrost"
```
This will enable to you to use the latest version of Bifrost. If you want to install from source, please see the advanced instructions.

**N.B You need to have Apache TVM installed. You can find installation instructions [here](https://tvm.apache.org/docs/install/index.html).**

## How to use

Bifrost extends TVM to support STONNE as an external library. Most of the workflow is identical to the usual TVM workflow, but with extra fucntionality defined to configure a simulated accelerator and dataflow mapping. To get started, simply import tvm and bifrost.
``` python
import tvm
import bifrost
```
Importing TVM and Bifrost in this order is essential. Bifrost overrides the LLVM operators and adds new external ones which calls the STONNE library. When importing bifrost a new directory called ```bifrost_temp``` is created in your current working directory. This directory stores the temporary files generated by Bifrost when running, the cycle output in cycles.json, and the detailed STONNE infromation if ```architecture.print_stats``` is enabled. This directory can be deleted after use (and you've made sure to get the data you need).

### Running a DNN model

When runnning a DNN model using Bifrost supported layers are automatically off-loaded to the simulated DNN accelerator and unsupported ones are executed on the TVM LLVM runtime backend. Currently, Bifrost supports NCHW conv2d and fully-connected (dense) layers. There is also support for NHWC conv2d layers, but the output is still unreliable at best. The simplest way to execute a DNN model is to use the built-in runners in Bifrost. Currently, PyTorch and ONNX models are supported.
``` python
 # Import the runner
from bifrost.runner.run import run_torch, run_onnx

# Get model and input
from alexnet import torch_model, input

# Run using Bifrost on STONNE. 
# If no architecture has been specified the default one will be used
output = run_torch(torch_model, input)
```

You can also run models from all deep learning libraries which are supported by TVM. Models from deep learning libraries other than PyTorch and ONNX can be used compiling them using TVM. [The TVM documentation contains gudies for PyTorch, Tensorflow, ONNX, MXNet, etc](https://tvm.apache.org/docs/tutorials/index.html#compile-deep-learning-models) models, just replace the target string with ```target = "llvm -libs=stone"```. The following example shows how to run a PyTorch model without using the Bifrost runner:

```python
# Import tvm and bifrost
import tvm
import bifrost

# Get model and input
from alexnet import torch_model, input

# Trace torch model and load into tvm
torch_model.eval()
trace = torch.jit.trace(torch_model, input).eval()
mod, params = relay.frontend.from_pytorch(trace, [("trace", input.shape)])

# Use STONNE as an external library
target = "llvm -libs=stonne"

# Run the model
lib = relay.build(mod, target=target, params=params)
ctx = tvm.context(target, 0)
module = runtime.GraphModule(lib["default"](ctx))
module.set_input("trace", input)
output = module.run()
```

### Configuring the simulated architecture
The general structure of a simulated DNN accelerator comprises of a spatial array of processing elements (PEs). Each PE contains a multiply-accumulate unit (MAC). The PEs receive their inputs and weights from the distribution network and write outputs back to the buffer using the reduction network:
![STONNE structure](https://drive.google.com/uc?export=view&id=15K-3DWHoYzPDFAWrTtioaOmvrL_8bMx0)

|Setting|Description|Options|
| --- | --- | --- |
| controller_type |The simulated architecture such as MAERI, SIGMA, and the TPU|"MAERI_DENSE_WORKLOAD", "SIGMA_SPARSE_GEMM", or "TPU_OS_DENSE"|
| ms_network_type |Defines the mulitplier type. Flexible architectures use LINEAR while rigid ones like the TPU must use OS_MESH |"LINEAR","OS_MESH"|
| ms_size | The number of multipliers (PEs) in the architecture, used if ms_network_type is LINEAR (not OS_MESH.)|Power of two and >= 8 |
| ms_row  | If ms_network_type is OS_MESH the PEs are organised into rows and columns,  |Power of two and >= 8|
| ms_col  | If ms_network_type is OS_MESH the PEs are organised into rows and columns,  |Power of two and >= 8|
| reduce_network_type |The type of reduction network|"ASNETWORK","FENETWORK","TEMPORALRN"|
| dn_bw | Number of read ports (distribution network)|Power of two and >= 8 |
| rn_bw | Number of write ports (reduction network)|Power of two and >= 8 |
| sparsity_ratio | The sparsity of the architecture|[0,10]|
| accumulation_buffer_enabled |Accumulation buffer, required to be enabled for rigid architectures like the TPU  |True or False|

To use the TPU the following settings are required:
|Setting|Selected Option|
| -- | -- |
|controller_type |TPU_OS_DENSE|
|ms_network_type|OS_MESH|
|ms_row|Integer which is a power two and >= 8|
|ms_col|Integer which is a power two and >= 8|
|accumulation_buffer_enabled|True|

The simulated architecture is configured through the architecture module:
``` python
# Import the architecture module 
from bifrost.stonne.simulator import architecture

# Configure the simulated architecture
architecture.ms_size = 128
architecture.rn_bw = 64
architecture.dn_bw = 64
architecture.controller_type = "SIGMA_SPARSE_GEMM"
architecture.sparsity_ratio = 0

# Create the config file which is used by STONNE
architecture.create_config_file()
```
If the architecture is not configured the following configuration is used:
|Option|Default|
| -- | -- |
|ms_size|16|
|reduce_network_type|ASNETWORK|
|ms_network_type|LINEAR|
|dn_bw|8|
|rn_bw|8|
|controller_type|MAERI_DENSE_WORKLOAD|
|accumulation_buffer_enabled|True|

By default STONNE will not create any output files during execution. This setting can be enabled by setting ```architecture.print_stats = True```

### Configure dataflow mapping

The energy efficiency and performance of DNN accelerator is determined by its *dataflow*. The computation is divided up by grouping neurons into \emph{tiles} which defines how a group of neurons' inputs, weights, and intermediate outputs (psums) are delivered and reused within the accelerator. This pattern is the dataflow in the accelerator. A mapping is a specific instance of a dataflow. In a reconfigurable accelerator, a workload can be scheduled and staged in many different ways depending on the mapping for that specific workload. MAERI and SIGMA are both reconfigurable accelerators. The SIGMA memory controller automatically generates a mapping based on the sparsity level, but when using the MAERI architecture this mapping must be manually provided (efficient mappings can be generated with the the help of AutoTVM).

The parameters which determine the a mapping in MAERI depend on the workload being executed. For convolutions the following parameters are used: 
|**Tile** | **Description**|
| --|--|
| T_R  | Number of filter rows mapped at a time                                  |  
| T_S  | Number of filter columns mapped at a time                               |  
| T_C  | Number of filter and input channels per group mapped at a time          |  
| T_K  | Number of filters and output channels per group mapped at a time        |  
| T_G  | Number of groups mapped at a time                                       |  
| T_N  | Number of inputs mapped at a time (Only 1 is supported so far by STONNE)|  
| T_X_ | Number of output rows mapped at a time                                 |
| T_Y_ | Number of input columns mapped a time  |

For fully connected layers:
|**Tile** | **Description**|
| --|--|
| T_M | Number of output neurons mapped at a time |
| T_N | Number of batches mapped at a time |
| T_K | Number of input neurons mapped at a time |  

When executing a DNN model on MAERI with a specific mapping you simply provide the mapping in the same order as the layers in the model are executed. The following example demonstrates how the mappings for the layers in Alexnet are provided, a CNN model with five conv layers followed by three fully connected layers. If no mapping is provided, a basic one will be generated with all parameters set to 1 (this will be very inefficient).
``` python
# Mappings can be provided as txt files
# Alexnet has five conv layers, these mappings will be applied in order
conv_mappings = [
 "path/to/conv_mapping1.txt",
 "path/to/conv_mapping2.txt",
 "",                          # Empty string, basic mapping will be used
 "path/to/conv_mapping4.txt",
 "path/to/conv_mapping5.txt",
]

# Mappings can also be provided as python dictionaries
fc_mappings = [
 {"T_S":12, "T_K":8, "T_N":1},
 {},  # Empty dictionary, basic mapping will be used
 {"T_S":8, "T_K":10, "T_N":1},
]

# The load_mapping from the architecture module is used
# to configure the mapping
architecture.load_mapping(
  conv = conv_mappings,
  fc = fc_mappings,
)
```

### Tuning 
When tuning the mapping or the hardware for a DNN, we first need to set 
``` python
from bifrost.stonne.simulator import architecture
# Set the tuning to true
architecture.tune = True

# I you want to tune using partial 
# sums instead of cycles:
architecture.tune_psums = True
```

The next step is choosing what paramaters you want to tune:

The settings column corresponds to the boolean value you need to set to true to include that parameter in the optimisation space. If the settings can be a range of values, the variable is used to set the search space:
|Setting|Variable|Valid options for variable|
| -- | -- | -- |
|tune_convolutions_tile|conv_range|List of integers|
|tune_fc_tile|fc_range|List of integers|
|tune_accumulation_buffer|N/A|N/A|
|tune_sparsity_ratio|sparsity_ratio_range|List of integers|
|tune_ms_size|ms_size_range|List of integers|
|tune_rn_bw|rn_bw_range|List of integers|
|tune_dn_bw|dn_bw_range|List of integers|

You need to access the tuning module to create the tuning space:
``` python
from bifrost.stonne.simulator import architecture
architecture.tuner
# Enable tuning
architecture.tune = True

# Tune ms_size
architecture.tuner.tune_ms_size = True
# Set the options for the tuning space
architecture.tuner.ms_size_range = [128,256,2048]

# Tune sparsity
architecture.tuner.tune_sparsity_ratio = True
# Set the options for the tuning space
architecture.tuner.sparsity_ratio_range = [0,20,40,60,80,100]
```

Here is a full example of tuning the dataflow for AlexNet:
``` python
from bifrost.stonne.simulator import config_simulator, architecture

# Set the architecture
architecture.ms_size = 128
architecture.dn_bw=64
architecture.rn_bw=64
architecture.controller_type = "MAERI_DENSE_WORKLOAD"
architecture.create_config_file()

# Enable tuning
architecture.tune = True

# Set tuning to be based on partial sums instead of cycles
architecture.tuner.tune_psums = True

# Tune mapping for both convolutions and fully connected layers
architecture.tuner.tune_convolutions_tile = True
architecture.tuner.tune_fc_tile = True

# Set the range to test
architecture.tuner.conv_num = 20
architecture.tuner.fc_num = 20

# For AutoTVM to work, a __name__ == "__main__" block is required. When tuning, 
# each unique combination of parameters represents a point in the tuning space.
# For each point, a new TVM instance is launched. All settings which you want
# to be constant across all instances have to be set outside of this block.
if __name__ == "__main__":
  # Standard imports
  import tvm
  import bifrost 

  from bifrost.tuner.stonne_builder import StonneLocalBuilder, StonneLocalRunner
  from tvm.autotvm.tuner import XGBTuner, GATuner, RandomTuner, GridSearchTuner
  
  from alexnet import alex_model as torch_model
  from alexnet import input_batch

  torch_model.eval()
  trace = torch.jit.trace(torch_model, input_batch).eval()
    
  mod, params = relay.frontend.from_pytorch(trace, [("trace", input_batch.shape)])


  target = "llvm --libs=stonne"
  
  # The output from the tuning process is placed in a separate file.
  # It is recommended to use bifrost_temp to make sure that all files arwe kept in the
  # same place.
  log_file = "bifrost_temp/alexnet.log"
  
  # Set the tuning options
  tuning_options = {
        "log_filename": log_file,
        "tuner": "xgb",
        "early_stopping": None,
        "measure_option": autotvm.measure_option(
            builder=StonneLocalBuilder(),
            runner=StonneLocalRunner(),
        ),
    }


  tasks = autotvm.task.extract_from_program(
            mod, 
            target=target, 
            params=params, 
            ops=(relay.op.get("nn.conv2d"),)
  )
  for i, task in enumerate(tasks):
    prefix = "[Task %2d/%2d] " % (i + 1, len(tasks))
    
    # Create the tuner
    tuner_obj = XGBTuner(task, loss_type="rank")

    # do tuning
    n_trial = len(task.config_space)/10


    tuner_obj.tune(
       n_trial=n_trial,
       measure_option=measure_option,
       callbacks=[
         autotvm.callback.progress_bar(100, prefix=prefix),
         autotvm.callback.log_to_file(log_filename),
    ],

```
## Dependecies


Python >=3.8
* Apache TVM |A deep learning compiler stack | https://tvm.apache.org
* STONNE |A cycle-accurate simulator for reconfigurable DNN accelerators written in C++, however a forked version is required for Bifrost| https://github.com/francisco-munoz/stonne
* JSONCPP |A library to read/write JSON files for C++| https://github.com/open-source-parsers/jsoncpp

## Tests
Bifrost includes a test suite to ensure the correctness of the supported operations. This will run all implemented layers (conv2d and dense) on STONNE and compare the output against the TVM LLVM implementation for correctness. The MAERI, SIGMA, and TPU architectures will be tested. You can run the tests using the following commands:
```
cd bifrost
python setup.py
```
Tested on macOS Big Sur (11.1) and Manjaro 20.2.1, the NCHW conv2d and dense tests pass. The NHWC tests do not.

# Benchmarks
Bifrost includes a number of tests and benchmarks. These are the benchmarks which are used in the evaluation section of the dissertation. These benchmarks can be found in the ```benchmarks``` directory. Please make sure TVM and Bifrost have been insatleld before running any of these.

## AlexNet
The AlexNet benchmarks is divided up into several files. The tune_alexnet.py file will tune the mapping space for the conv and fc layer for the MAERI architecture. Please cd into the ```benchmarks/alexnet``` folder tu run this. The tuning log will be placed in the ```benchmarks/alexnet/evaluation``` folder. The log be parsed using the parse_log_benchmark.py file to find the efficient mappings produced by Bifrost's AutoTVM module. 

The run_alexnet.py is used to execute both the MAERI and SIGMA evaluations from the dissertation, instructions on how to use can be found at mthe top of the file.

In the ```benchmarks/alexnet/evaluation``` directory all the AlexNet figures from the dissertation can be found. These can be prdouced by running the figures.py file.

The ```benchmarks/alexnet/tiles``` contains mapping files for AlexNet. The basic mapping sets all tiles to 1, the opt mappings are the mapping produced by Bifrost, the performance mappings are the mappings produced by mRNA, and the stonne_paper mappings are the mapping from the STONNE paper to execute AlexNet.

## Conv2d MAPPING example.
This benchmark is used to demonstrate the importance of proper dataflow orchestration for reconfigurable architectures. The tune_conv2d.py explores the whole mapping space [1-20]for a small convolution using ms_size in the range [8,16,32,64,128]. The output log is placed in the ```benchmarks/conv2d/evaluation``` directory, This log can be parsed using parse_log_and_create_fig.py which will also produce the figures used in the dissertation.

## Other benchmrks
The resnet and vgg evaluations should work, but they have not been documented properly and are very slow. 

# Example scripts
Bifrost ships with a number of example scripts which show typical use cases for Bifrost and are used to orient users on how to perfrom some basic actions. These assume TVM knowledge. The following table explains these files in detail:
|File Name|Description|
|--|--|
|example_conv2d|Demonstrates how to execute a NCHW convolution and compares output to LLVM. |
|example_dense |Demonstrates how to execute a dense operator (fully connected) and compares output to LLVM.|
|example_conv2d_nhwc |Demonstrates how to execute a NHWC convolution and compares output to LLVM. It also shows how NHWC convolutions currently do not work properly. |
|example_tensorflow|Demonstrates how to a deep learning framework like TensorFlow.|
|example_conv2d_opt |Demonstrates how to tune a small network. This examples tunes the ms_size range on cycles.|

# Advanced Instructions 
## Build from source

Install Apache TVM using the installation instructions [here](https://tvm.apache.org/docs/install/index.html).

Cd into bifrost
```
cd bifrost
```
You can now install it by running setup.py:
```
python setup.py install 
```
You can now use Bifrost.

Alternatively, if you are going to make modifications to Bifrost then export it to PYTHONPATH to tell python where to find the library. This way your changes will immeditaly be reflected and there is no need to call setup.py again.
```
export BIFROST=/path/to/level-4-project/bifrost/
export PYTHONPATH=$BIFROST/python:${PYTHONPATH}
```


## Bifrost Deep Dive
The following diagram shows an overview of Bifrost.
![Bifrost diagram](https://drive.google.com/uc?export=view&id=1YNvC9asfmgpLy4Pl6nDMuHG23A1TneEj)

### Bifrost TOPI Strategies
These can found be under ```bifrost/bifrost/stonne/ops/```. Currently conv2d and dense (fully connected) operators are fully implemented, these operators are exposed through ```__init__.py``` in the same directory. Both operators are implemented in the same fashion. First the Relay strategies are redefined:
``` python 
@conv2d_strategy.register("cpu")
def conv2d_strategy_cpu(attrs, inputs, out_type, target):
# Dense strategies are redefined in the same fashion as above
``` 
which means that when Bifrost is imported the TVM llvm strategies are overriden. In the new strategies, new implementation are added when "stonne" is included in target.libs:
``` python
# Example from conv2d.py
if "stonne" in target.libs:
    if layout == "NCHW":
        assert kernel_layout == "OIHW"
        strategy.add_implementation(
                wrap_compute_conv2d(conv2d_stonne_nchw),
                wrap_topi_schedule(schedule_conv2d_stonne_nchw),
                name="conv2d_stonne.x86",
        )
```
Each implementation includes a scheduling function and a compute function. STONNE does not include support for us to schedule the offloaded operators and as such dummy schedule functions are used instead:
``` python
# Example from conv2d.py
# Create a dummy schedule which does nothing
@autotvm.register_topi_schedule("conv2d_stonne_nchw.x86")
def schedule_conv2d_stonne_nchw(cfg, outs):
    """Create schedule for conv2d_nhwc"""
    cfg.add_flop(1) # Add a flop estimator as AutoTVM breaks othnerwise (even if the flop is never used)
    return te.create_schedule([x.op for x in outs])
```
The compute function is where the the execution of the operator is offloaded to STONNE. First the layer infromation is parsed and the output dimenions are calculated depending on the operator. It is in the compute function where *tuning knobs* are implemented. A tuning knob is a tuple with a parameter and a list of options which the AutoTVM module uses to define the tuning space. An example of a tuning knob is ```("T_X", [0,1,2,3,4,5,6,7,8,9,10])``` where ```T_X``` is MAERI dataflow tile and the list is a number of options. These knobs are fetched from the ```tuner``` module:
```python
# Define tuning space
if architecture.tune:
    # Get and register the tuning knobs
    knobs = architecture.tuner.create_knobs(conv = True)
    for knob in knobs:
        cfg.define_knob(*knob)
    
    # Config architecture and set dataflow mapping using the knobs (parameters)
    # selected by AutoTVM. 
    architecture.config(cfg, conv = True)
```
Finally, the compute function returns an external tensor function which calls the corresponding function from the STONNE-Bifrost API:
``` python
return te.extern(
    (N,K,X_, Y_), # Output dimensions calculated above
    [data,kernel], # The "ins" data 
    lambda ins, outs: tvm.tir.call_packed(
            
        # The name of the corresponding function in the STONNE-Bifrost API
        "tvm.contrib.stonne.conv2d.nchw",  
        # Parameters such as layer information, architecture configuration, and mapping
        architecture.path, # [0]
        ..., # Leave out options  for brevity
        ins[0],            # [24] # Data
        ins[1],            # [25] # Weight (kernel)
        outs[0],           # [26] # Output (array of floats) 
        ),
    name = "s",
    dtype = out_dtype
)
```

### STONNE-Bifrost API

The STONNE-Bifrost API is a collection of functions written in C++ which bridges TVM with STONNE. The compiled binary ```stonne_lib.so``` is included in the ```bifrost/bifrost/stonne/stonne_lib"```. When importing Bifrost the ```load_lib``` function from ```bifrost/bifrost/stonne/connect_stonne.py"``` is called. This function loads the .so binary using ctypes and exposes the fucntions defined in the API to TVM.
#### Functions
For each new operator in the Bifrost TOPI strategies, a corresponding function is defined in the STONNE-Bifrost API.  Each function is registered to TVM's global function registry using type erased functions:
```cpp
TVM_REGISTER_GLOBAL("tvm.contrib.stonne.conv2d.nchw")
    .set_body([](TVMArgs args, TVMRetValue *ret) {
        std::string path_to_arch_file = args[0];
        ...,
        DLTensor *input = args[24];
        DLTensor *weight = args[25];
        DLTensor *output = args[26];
```
All functions follow the same general pattern, first the function is registered as above. Then the simulated architecture on STONNE is intialised:
```cpp
//Creating config  to find out if we are going to
// run a dense or sparse simulation
Config stonne_config;
if (path_to_arch_file != "")
{
    stonne_config.loadFile(path_to_arch_file);
}
// Set output files
stonne_config.print_stats_enabled = stats;
```
Depending on the simulated architecture, the input (data) and weight float arrays are modified for execution on STONNE. For example NCHW conv2d on MAERI requires a conversion to NHWC and additional padding, while for the SIGMA architecture im2col is applied to the input array as the convolution is executed as a matrix multiplication. Finally the workload is executed on STONNE using a fucntion from the STONNE API:
``` cpp
cost = simulateDenseConvForward(layer_name,...,stonne_config); # Get the cycle cost
```
STONNE has been forked specifically for Bifrost and can be found here: https://github.com/axelstjerngren/stonne. The forked version of STONNE includes an extended API for STONNE.
Finally, the cost (cycles) is recorded to ```bifrost_temp/cycles.json```. If the user is tuning, the cost (either cycles or psums) is also recorded to ```bifrost/bifrost/stonne/data/costs.json```.  

#### Modifying the C++ code in the STONNE-Bifrost API. 
All of the C++ files can be found under:
```
level-4-project
|___bifrost
|    |__src
|    |   |__include
|    |   |     |__cost.h
|    |   |
|    |   |__conv_forward.cpp
|    |   |__cost.cpp
|    |   |__json.cpp
|    |   |__etc...
|    |__Makefile
```

Any new .cpp files will be automatically found by the Makefile as long as they are created within the /src folder. Before you compile the code you need STONNE and TVM as enviroment variables (see next section) You can the compile your new code with the following commands:
```
cd bifrost
make -j
```

#### C++ depdencies 
To change the C code you need to clone the STONNE, mRNA and TVM repositories:
```
git clone https://github.com/axelstjerngren/stonne
git clone https://github.com/axelstjerngren/mrna
git clone https://github.com/apache/tvm
```
Keeping these three in the same folder will be useful.
Before you can run **make** you need to export two environment variables:
```
export TVM_ROOT    = path_to_tvm/tvm
export STONNE_ROOT = path_to_stonne/stonne
```
The C++ should now compile correctly when you run **make** inside of the /bifrost directory.

### Simulator configurator
This module can be found in ```bifrost/bifrost/stonne/simulator.py```. The simulated architecture is contained in a class called ```Simulator```:
```python
class Simulator(object):
    def __init__(self):
        #
        self._ms_size:int= 16
        ... # Variables for all other architecture parameters
```
Each architecture variable has a corresponding getter and setter. The setter function validates the user input and makes sure that the user is not able to create invalid configurations:
```python
@property
def ms_size(self):
    return self._ms_size

@ms_size.setter
def ms_size(self, size: int):
    # Use bit manipulation magic to check if power of two
    # Size also has to be >=8
    if (size & (size-1) == 0) and size != 0 and size>=8:
        self._ms_size = size
    else:
        raise ConfigError("ms_size has to be a power of two!")
```
STONNE requires .cfg files as input to configure the simulated accelerator. The architecture contains a fucntion to generate config files which are created in the ```bifrost_temp/architecture``` directory:
``` python
def create_config_file(self):
    """
    This will create a config file for STONNE

    """
    # Create a file
    with open(self.path, "w+") as f:
        f.write("[MSNetwork]\n")
        ...
        f.write(f'controller_type="{self.controller_type}"\n')
```
### Mapping configurator
The mapping configurator just takes mappings parameters and produces files. STONNE is able to validate these mappings without the need for external checks.
### AutoTVM Module

The AutoTVM module consists of several modules:

```bifrost/bifrost/tuner/stonne_builder.py```
Tuning using AutoTVM uses local RPC devices. The stonne_builder overrides these to upload the STONNE-Bifrost API .so file. It also overwrites the cost function/

```bifrost/bifrost/tuner/parameters.py```
This is where the tunable parameters are defined.


