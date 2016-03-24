#!/usr/bin/env python3
#
# Converter from Keras saved NN to JSON
"""
____________________________________________________________________
Variable specification file

In additon to the standard Keras archetecture and weights files, you
must provide a "variable specification" json file with the following
format:

  {
    {"inputs": [
      {"name": variable_name,
       "scale": scale,
       "offset": offset,
       "default": default_value},
      ...
      ] }
    {"class_labels": [output_class_1_name, output_class_2_name, ...] }
  }

where `scale` and `offset` account for any scaling and shifting to the
input variables in preprocessing. The "default" value is optional.

"""

import argparse
import json
import h5py
import numpy as np

def _run():
    """Top level routine"""
    args = _get_args()
    with open(args.arch_file, 'r') as arch_file:
        arch = json.load(arch_file)
    with open(args.variables_file, 'r') as inputs_file:
        inputs = json.load(inputs_file)
    with h5py.File(args.hdf5_file, 'r') as h5:
        out_dict = {
            'layers': _get_layers(arch, h5),
        }
        out_dict.update(_parse_inputs(inputs))
    print(json.dumps(out_dict, indent=2))

def _get_args():
    parser = argparse.ArgumentParser(
        description="Converter from Keras saved NN to JSON",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('arch_file', help='architecture json file')
    parser.add_argument('variables_file', help='variable spec as json')
    parser.add_argument('hdf5_file', help='Keras weights file')
    return parser.parse_args()

_activation_map = {
    'relu': 'rectified',
    'sigmoid': 'sigmoid',
}

# __________________________________________________________________________
# Layer converters
#
# Each of these converters takes two arguments:
#  - An H5 Group with the layer parameters
#  - The number of inputs (for error checking)
#
# Each returns two outputs:
#  - A dictionary of layer information which can be serialized to JSON
#  - The number of outputs (also for error checking)

def _get_dense_layer_parameters(layer_group, n_in):
    """Get weights, bias, and n-outputs for a dense layer"""
    weights = layer_group['param_0']
    bias = layer_group['param_1']
    assert weights.shape[1] == bias.shape[0]
    assert weights.shape[0] == n_in
    # TODO: confirm that we should be transposing the weight
    # matrix the Keras case
    return_dict = {
        'weights': np.asarray(weights).T.flatten('C').tolist(),
        'bias': np.asarray(bias).flatten('C').tolist(),
        'architecture': 'dense'
    }
    return return_dict, weights.shape[1]


def _get_maxout_layer_parameters(layer_group, n_in):
    """Get weights, bias, and n-outputs for a maxout layer"""
    raise NotImplementedError

_layer_converters = {
    'dense': _get_dense_layer_parameters,
    'maxout': _get_maxout_layer_parameters,
    }

# __________________________________________________________________________
# master layer converter / inputs function

def _get_layers(network, h5):
    layers = []
    in_layers = network['layers']
    n_out = h5['layer_0']['param_0'].shape[0]
    for layer_n in range(len(in_layers)):
        # get converter for this layer
        layer_arch = in_layers[layer_n]
        layer_type = layer_arch['name'].lower()
        convert = _layer_converters[layer_type]

        # get the hdf5 info
        layer_group = h5['layer_{}'.format(layer_n)]

        # build the out layer
        out_layer, n_out = convert(layer_group, n_out)
        out_layer['activation'] = _activation_map[layer_arch['activation']]
        layers.append(out_layer)
    return layers

def _parse_inputs(keras_dict):
    inputs = []
    defaults = {}
    for val in keras_dict['inputs']:
        inputs.append({x: val[x] for x in ['offset', 'scale', 'name']})

        # maybe fill default
        default = val.get("default")
        if default is not None:
            defaults[val['name']] = default
    return {
        'inputs': inputs,
        'outputs': keras_dict['class_labels'],
        'defaults': defaults,
    }

if __name__ == '__main__':
    _run()
