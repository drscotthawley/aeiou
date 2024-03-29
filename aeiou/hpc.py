# AUTOGENERATED! DO NOT EDIT! File to edit: ../05_hpc.ipynb.

# %% auto 0
__all__ = ['get_accel_config', 'HostPrinter', 'save', 'load', 'n_params', 'freeze']

# %% ../05_hpc.ipynb 5
import yaml
import accelerate
from pathlib import Path
import tqdm
import torch
import torchaudio
from torchaudio import transforms as T
import os


# %% ../05_hpc.ipynb 6
def get_accel_config(filename='~/.cache/huggingface/accelerate/default_config.yaml'):
    "get huggingface accelerate config info" 
    try:  # first try to use the default file
        filename = filename.replace('~', str(Path.home()))
        with open(filename, 'r') as file:
            ac =  yaml.safe_load(file)
    except OSError:
        ac = {}
        
    # then update using any environment variables
    if os.getenv('MAIN_PROCESS_IP') is not None: ac['main_process_ip'] = os.getenv('MAIN_PROCESS_IP')
    if os.getenv('MACHINE_RANK')    is not None: ac['machine_rank']    = os.getenv('MACHINE_RANK')
    if os.getenv('NUM_MACHINES')    is not None: ac['num_machines']    = os.getenv('NUM_MACHINES')
    if os.getenv('NUM_PROCESSES')   is not None: ac['num_processes']   = os.getenv('NUM_PROCESSES')

    return ac

# %% ../05_hpc.ipynb 10
class HostPrinter():
    "lil accelerate utility for only printing on host node"
    def __init__(
        self, 
        accelerator,    # huggingface accelerator object
        tag='\033[96m', # starting color
        untag='\033[0m' # reset to default color
    ): 
        self.accelerator, self.tag, self.untag = accelerator, tag, untag
    def __call__(self, s:str):
        if self.accelerator.is_main_process:
            print(self.tag + s + self.untag, flush=True)

# %% ../05_hpc.ipynb 14
def save(
    accelerator, # Huggingface accelerator object
    args,        # prefigure args dict, (we only use args.name)
    model,       # the model, pre-unwrapped
    opt=None,    # optimizer state
    epoch=None,  # training epoch number
    step=None    # training setp number
    ):
    "for checkpointing & model saves"
    #accelerator.wait_for_everyone() # hangs
    filename = f'{args.name}_{step:08}.pth' if (step is not None) else f'{args.name}.pth'
    if accelerator.is_main_process:
        print(f'\nSaving checkpoint to {filename}...')
    obj = {'model': accelerator.unwrap_model(model).state_dict() }
    if opt is not None:   obj['opt'] = opt.state_dict()
    if epoch is not None: obj['epoch'] = epoch
    if step is not None:  obj['step'] = step
    accelerator.save(obj, filename)

# %% ../05_hpc.ipynb 15
def load(
    accelerator, # Huggingface accelerator object
    model,       # an uninitialized model (pre-unwrapped) whose weights will be overwritten
    filename:str, # name of the checkpoint file
    opt=None,    # optimizer state UNUSED FOR NOW
    ):
    "load a saved model checkpoint"
    #accelerator.wait_for_everyone() # hangs
    if accelerator.is_main_process:
        print(f'\nLoading checkpoint from {filename}...')
    accelerator.unwrap_model(model).load_state_dict(torch.load(filename)['model'])
    return model # this return isn't actually needed since model is already updated at this point

# %% ../05_hpc.ipynb 17
def n_params(
    module # raw PyTorch model/module, e.g. returned by accelerator.unwrap_model()
    ):
    """Returns the number of trainable parameters in a module.
    Be sure to use accelerator.unwrap_model when calling this.  """
    return sum(p.numel() for p in module.parameters())

# %% ../05_hpc.ipynb 18
def freeze(
    model  # raw PyTorch model, e.g. returned by accelerator.unwrap_model()
    ):
    """freezes model weights; turns off gradient info
    If using accelerate, call thisaccelerator.unwrap_model when calling this.  """
    for param in model.parameters():  
        param.requires_grad = False
