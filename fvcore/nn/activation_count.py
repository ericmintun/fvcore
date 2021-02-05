import typing

import torch.nn as nn
from fvcore.nn.jit_analysis import JitModelAnalysis
from fvcore.nn.jit_handles import generic_activation_jit


# A dictionary that maps supported operations to their activation count handles.
# pyre-fixme[24]: Generic type `typing.Callable` expects 2 type parameters.
_DEFAULT_SUPPORTED_OPS: typing.Dict[str, typing.Callable] = {
    "aten::_convolution": generic_activation_jit("conv"),
    "aten::addmm": generic_activation_jit("addmm"),
}


def default_activation_counter(
    model: nn.Module,
    inputs: typing.Tuple[object, ...],
    additional_ops: typing.Dict[str, typing.Callable] = {},
) -> JitModelAnalysis:
    """
    Constructs a JitModelAnalysis class configured for activation counting.
    By default, counts the flops for convolutional and linear layers and
    returns results in mega-activations.
    Args:
        model (nn.Module): The model to compute flop counts.
        inputs (tuple): Inputs that are passed to `model` to count flops.
            Inputs need to be in a tuple.
        additional_ops (dict(str,Callable) or None) : provide additional
            handlers for extra ops, or overwrite the existing handlers for
            convolution and matmul and einsum. The key is operator name and the value
            is a function that takes (inputs, outputs) of the op. We count
            one Multiply-Add as one FLOP.
    Returns:
        JitModelAnalysis : computes and stores flop counts, organized
            by module and by operator type.
    """
    ops_handles = {**_DEFAULT_SUPPORTED_OPS, **(additional_ops or {})}
    act_counter = JitModelAnalysis(model, inputs, ops_handles)
    act_counter.set_output_scale("mega")
    return act_counter


def activation_count(
    model: nn.Module,
    inputs: typing.Tuple[object, ...],
    # pyre-fixme[24]: Generic type `typing.Callable` expects 2 type parameters.
    supported_ops: typing.Union[typing.Dict[str, typing.Callable], None] = None,
) -> typing.Tuple[typing.DefaultDict[str, float], typing.Counter[str]]:
    """
    Given a model and an input to the model, compute the total number of
    activations of the model.
    Args:
        model (nn.Module): The model to compute activation counts.
        inputs (tuple): Inputs that are passed to `model` to count activations.
            Inputs need to be in a tuple.
        supported_ops (dict(str,Callable) or None) : provide additional
            handlers for extra ops, or overwrite the existing handlers for
            convolution and matmul. The key is operator name and the value
            is a function that takes (inputs, outputs) of the op.
    Returns:
        tuple[defaultdict, Counter]: A dictionary that records the number of
            activation (mega) for each operation and a Counter that records the
            number of skipped operations.
    """

    act_counter = default_activation_counter(model, inputs, supported_ops)
    return act_counter.by_operator(), act_counter.skipped_ops()
