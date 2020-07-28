# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import torch

from nemo.core import Typing, typecheck
from nemo.core.neural_types import *


class TestNeuralTypeCheckSystem:
    @pytest.mark.unit
    def test_no_types_passthrough(self):
        class NoTypes(Typing):
            @typecheck()
            def __call__(self, x):
                return torch.tensor(1.0)

        obj = NoTypes()
        result = obj(torch.tensor(1.0))

        assert result == torch.tensor(1.0)
        assert not hasattr(result, 'neural_type')

    @pytest.mark.unit
    def test_input_output_types(self):
        class InputOutputTypes(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {"y": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x):
                x += 1
                return x

        obj = InputOutputTypes()
        result = obj(x=torch.zeros(10))

        assert result.sum() == torch.tensor(10.0)
        assert result.neural_type.compare(NeuralType(('B',), ElementType())) == NeuralTypeComparisonResult.SAME

        # Test passing wrong key for input
        with pytest.raises(TypeError):
            _ = obj(a=torch.zeros(10))

        # Test using positional args
        with pytest.raises(TypeError):
            _ = obj(torch.zeros(10))

    @pytest.mark.unit
    def test_input_types_only(self):
        class InputTypes(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x):
                x += 1
                return x

        obj = InputTypes()
        result = obj(x=torch.zeros(10))

        assert result.sum() == torch.tensor(10.0)
        assert hasattr(result, 'neural_type') is False

    @pytest.mark.unit
    def test_output_types_only(self):
        class OutputTypes(Typing):
            @property
            def output_types(self):
                return {"y": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x):
                x += 1
                return x

        obj = OutputTypes()
        result = obj(x=torch.zeros(10))

        assert result.sum() == torch.tensor(10.0)
        assert result.neural_type.compare(NeuralType(('B',), ElementType())) == NeuralTypeComparisonResult.SAME

        # Test passing positional args
        # Positional args allowed if input types is not set !
        result = obj(torch.zeros(10))
        assert result.sum() == torch.tensor(10.0)

    @pytest.mark.unit
    def test_incorrect_inheritance(self):
        class IncorrectInheritance(object):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {"y": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x):
                x += 1
                return x

        obj = IncorrectInheritance()

        with pytest.raises(RuntimeError):
            _ = obj(x=torch.zeros(10))

    @pytest.mark.unit
    def test_port_definition_rejection(self):
        class InputPortDefinitionRejection(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {"w": NeuralType(('B',), ElementType()), "u": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x, y):
                x += 1
                y -= 1
                return x, y

        # Test input port mismatch
        obj = InputPortDefinitionRejection()

        with pytest.raises(TypeError):
            _ = obj(x=torch.zeros(10), y=torch.zeros(10))

        class OutputPortDefinitionRejection(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {
                    "w": NeuralType(('B',), ElementType()),
                }

            @typecheck()
            def __call__(self, x):
                return x + 1, x - 1

        obj = OutputPortDefinitionRejection()

        with pytest.raises(TypeError):
            _ = obj(x=torch.zeros(10))

    @pytest.mark.unit
    def test_positional_args(self):
        # Test positional check on input type
        class InputPositional(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x):
                x += 1
                return x

        obj = InputPositional()

        with pytest.raises(TypeError):
            _ = obj(torch.zeros(10))

        # Test positional pass-through for only output ports defined
        # NOTE: This is required behaviour to support type checking of NeMo Dataset class
        # during collate_fn() call.
        class OutputPositionalPassthrough(Typing):
            @property
            def output_types(self):
                return {"y": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x):
                x += 1
                return x

        obj = OutputPositionalPassthrough()
        result = obj(torch.zeros(10))

        assert result.sum() == torch.tensor(10.0)

    @pytest.mark.unit
    def test_optional_types(self):
        class InputOptionalTypes(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType()), "y": NeuralType(('B',), ElementType(), optional=True)}

            @typecheck()
            def __call__(self, x, y=None):
                if y is None:
                    x += 1
                else:
                    x += y
                return x

        obj = InputOptionalTypes()
        result = obj(x=torch.zeros(10))

        assert result.sum() == torch.tensor(10.0)
        assert hasattr(result, 'neural_type') is False

        result2 = obj(x=torch.zeros(10), y=torch.full([10], fill_value=5))

        assert result2.sum() == torch.tensor(10 * 5)
        assert hasattr(result, 'neural_type') is False

    @pytest.mark.unit
    def test_input_output_neural_types(self):
        class NodeA(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {"y": NeuralType(('B', 'D'), LogitsType())}

            @typecheck()
            def __call__(self, x):
                y = torch.randn(x.shape[0], 4)
                return y

        class NodeB(Typing):
            @property
            def input_types(self):
                return {"w": NeuralType(('B', 'D'), LogitsType())}

            @property
            def output_types(self):
                return {"u": NeuralType(('B',), LabelsType())}

            @typecheck()
            def __call__(self, w):
                _, u = w.max(-1)
                return u

        nodeA = NodeA()
        nodeB = NodeB()

        outA = nodeA(x=torch.zeros(10))
        outB = nodeB(w=outA)

        assert outB.shape == torch.Size([10])
        assert outB.neural_type.compare(NeuralType(('B',), LabelsType())) == NeuralTypeComparisonResult.SAME

    @pytest.mark.unit
    def test_nested_input_output_neural_types(self):
        class NestedNodeA(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {
                    "y0": NeuralType(('B', 'D'), LogitsType()),
                    "y1": NeuralType(('B', 'D'), LogitsType()),
                }

            @typecheck()
            def __call__(self, x):
                # input x = [[x1, x2], [x3]]
                x0 = x[0][0]
                y = torch.randn(x0.shape[0], 4)
                return [[y, y], [y]]

        # Non-homogeneous output types
        class NestedNodeB(Typing):
            @property
            def input_types(self):
                return {"w": NeuralType(('B', 'D'), LogitsType())}

            @property
            def output_types(self):
                return {
                    "u0": NeuralType(('B',), LogprobsType()),  # check non homogeneous type
                    "u1": NeuralType(('B',), LabelsType()),
                }

            @typecheck()
            def __call__(self, w):
                # input x = [[x1, x2], [x3]]
                _, u00 = w[0][0].max(-1)
                _, u01 = w[0][1].max(-1)
                _, u10 = w[1][0].max(-1)
                return [[u00, u01], [u10]]

        nodeA = NestedNodeA()
        nodeB = NestedNodeB()

        input_nest = [[torch.zeros(10), torch.zeros(10)], [torch.zeros(10)]]
        outA = nodeA(x=input_nest)
        outB = nodeB(w=outA)

        # Perform recursive shape assert
        def recursive_assert_shape(x, shape):
            if isinstance(x, list) or isinstance(x, tuple):
                for xi in x:
                    recursive_assert_shape(xi, shape)
                return

            assert x.shape == shape

        recursive_assert_shape(outB, torch.Size([10]))

        # Assert non-homogeneous type assertions
        assert outB[0][0].neural_type.compare(NeuralType(('B',), LogprobsType())) == NeuralTypeComparisonResult.SAME
        assert outB[0][1].neural_type.compare(NeuralType(('B',), LogprobsType())) == NeuralTypeComparisonResult.SAME
        assert outB[1][0].neural_type.compare(NeuralType(('B',), LabelsType())) == NeuralTypeComparisonResult.SAME

    @pytest.mark.unit
    def test_multi_forward_type(self):
        class AdaptiveTypeCheck(Typing):
            @property
            def input_types(self):
                if self.mode == 'train':
                    return {"x": NeuralType(('B',), ElementType())}

                elif self.mode == 'infer':
                    return {"y": NeuralType(('B',), ChannelType())}

                elif self.mode == 'eval':
                    return {"x": NeuralType(('B',), ElementType()), "y": NeuralType(('B',), ChannelType())}
                else:
                    raise ValueError("Wrong mode of operation")

            @property
            def output_types(self):
                if self.mode == 'train':
                    return {"u": NeuralType(('B',), ElementType())}

                elif self.mode == 'infer':
                    return {"v": NeuralType(('B',), ChannelType())}

                elif self.mode == 'eval':
                    return {"u": NeuralType(('B',), ElementType()), "v": NeuralType(('B',), ChannelType())}
                else:
                    raise ValueError("Wrong mode of operation")

            def __init__(self):
                self.mode = 'train'

            def __call__(self, **kwargs):
                # Call should call and forward appropriate method in its own mode
                if self.mode == 'train':
                    return self.train_forward(x=kwargs['x'])

                elif self.mode == 'eval':
                    return self.eval_forward(x=kwargs['x'], y=kwargs['y'])

                elif self.mode == 'infer':
                    return self.infer_forward(y=kwargs['y'])

            @typecheck()
            def train_forward(self, x):
                return x + 10

            @typecheck()
            def eval_forward(self, x, y):
                return x - 1, y - 1

            @typecheck()
            def infer_forward(self, y):
                return y - 10

            @property
            def mode(self):
                return self._mode

            @mode.setter
            def mode(self, val):
                if val not in ['train', 'infer', 'eval']:
                    raise ValueError('mode must be either train infer or eval')
                self._mode = val

        obj = AdaptiveTypeCheck()

        x = torch.zeros(10)
        y = torch.full([10], fill_value=5)

        obj.mode = 'train'
        x = obj(x=x)

        assert torch.all(x == 10)
        assert x.neural_type.compare(NeuralType(('B',), ElementType())) == NeuralTypeComparisonResult.SAME

        obj.mode = 'eval'
        x, y = obj(x=x, y=y)

        assert torch.all(x == 9)
        assert torch.all(y == 4)
        assert x.neural_type.compare(NeuralType(('B',), ElementType())) == NeuralTypeComparisonResult.SAME
        assert y.neural_type.compare(NeuralType(('B',), ChannelType())) == NeuralTypeComparisonResult.SAME

        obj.mode = 'infer'
        y = obj(y=y)

        assert torch.all(y == -6)
        assert y.neural_type.compare(NeuralType(('B',), ChannelType())) == NeuralTypeComparisonResult.SAME

        # Now perform assertions of wrong mode with wrong input combinations
        obj.mode = 'train'

        # In train mode, call infer
        with pytest.raises(TypeError):
            _ = obj.eval_forward(x=x, y=y)

        with pytest.raises(TypeError):
            # wrong input + wrong mode
            _ = obj.infer_forward(x=x)

    @pytest.mark.unit
    def test_disable_typecheck(self):
        class InputOutputTypes(Typing):
            @property
            def input_types(self):
                return {"x": NeuralType(('B',), ElementType())}

            @property
            def output_types(self):
                return {"y": NeuralType(('B',), ElementType())}

            @typecheck()
            def __call__(self, x, **kwargs):
                x += 1
                return x

        # Disable typecheck tests
        typecheck.set_typecheck_enabled(enabled=False)

        obj = InputOutputTypes()

        # Execute function without kwarg
        result = obj(torch.zeros(10))

        assert result.sum() == torch.tensor(10.0)
        assert hasattr(result, 'neural_type') is False

        # Test passing wrong key for input
        _ = obj(a=torch.zeros(10), x=torch.zeros(5))