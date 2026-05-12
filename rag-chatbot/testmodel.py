import torch
import numpy
import transformers

print("Torch:", torch.__version__)
print("NumPy:", numpy.__version__)
print("Transformers:", transformers.__version__)
print("MPS:", torch.backends.mps.is_available())
