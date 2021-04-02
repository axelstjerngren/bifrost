# Bifrost

Bifrost (/ˈbɪvrɒst/) is a tool for evaulation and optimization of DNN accelerators. The Bifrost interface bridges [Apache TVM](https://tvm.apache.org) (a deep learning compiler) with [STONNE](https://arxiv.org/pdf/2006.07137.pdf) (a simulator for DNN accelerators).

The name is taken from Norse mythology, where Bifrost is the bridge between Midgard and Asgard. 

# Quickstart Guide

## Installation
*Bifrost* is a Python tool. You can install it with one command:
```
pip install git+https://github.com/axelstjerngren/level-4-project#"egg=bifrost&subdirectory=bifrost"
```
This will enable to you to use the latest version of Bifrost.
**N.B** You need to have Apache TVM installed. You can find installation instructions [here](https://tvm.apache.org/docs/install/index.html).

## How to use

All scripts which use must import TVM and Bifrost:
``` python
import tvm
import bifrost
```
Importing TVM and Bifrost in this order is essential. Bifrost overrides the LLVM operators and adds new external ones which calls the STONNE library.


### Running a model
There are two ways to run a model.

The simplest version 


``` python

```


### Configuring the simulated architecture

``` python
from bifrost.stonne.simulator import architecture
```

Adter configuration you need to make sure thst a configuration file has been created.
``` python
architecture.create_config_file()
```


``` python

```

controller_type
ms_size 


### Tuning 
When tuning the mapping or the hardware for a DNN, we first need to set 
``` python
from bifrost.stonne.simulator import architecture

# Set the tuning to true
architecture.tune = True

```
You need to access the tuning module to create the tuning space
``` python
architecture.tuner
```

An example of tuning is availble in ```becnhmarks/alexnet/alexnet_tune.py```











# Advanced Instructions 
## Build from source

Install Apache TVM using the installation instructions [here](https://tvm.apache.org/docs/install/index.html).

Clone the project and cd into bifrost
```
git clone https://github.com/axelstjerngren/level-4-project
cd level-4-project/bifrost
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

## Modifying the C++ code 
All of the C++ files can be found in under:
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

Any new .cpp files will be automatically found by the Makefile as long as they are created within the /src folder. Before you compile the code you need STONNE, mRNA and TVM as enviroment variables (see next section) You can the compile your new code with the following commands:
```
cd bifrost
make -j
```

### C++ depdencies 
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
export MRNA_ROOT   = path_to_stonne/stonne
```
The C++ should now compile correctly when you run **make** inside of the level-4-project/bifrost directory.

## Dependecies


Python >=3.8
* Apache TVM |  | 
* STONNE |A cycle-accurate simulator for reconfigurable DNN accelerators written in C++, a forked version is required for Bifrost| 
]* JSONCPP |A library to read/write JSON files for C++| https://github.com/open-source-parsers/jsoncpp

STONNE
TVM
MRNA

**N.B** If you have TVM installed, you only need to run the pip command above. The C++ dependencies come pre-packaged together with Bifrost

## Run the tests
Bifrost includes a test suite to ensure the correctness of the supported operations. This will run all implemented layers (conv2d and dense) on STONNE and compare the output against the TVM LLVM implementation for correctness. The MAERI, SIGMA, and TPU architectures will be tested. You can run the tests using the following commands:
```
cd bifrost
python setup.py
```
Tested on macOS Big Sur (11.1) and Manjaro 20.2.1 

### Architecture

![Bifrost diagram](https://drive.google.com/uc?export=view&id=1YNvC9asfmgpLy4Pl6nDMuHG23A1TneEj)




