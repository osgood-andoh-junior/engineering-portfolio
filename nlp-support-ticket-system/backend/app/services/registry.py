from collections.abc import Callable

from ml.src.interfaces import Classifier
from ml.src.models.attention import AttentionClassifier
from ml.src.models.naive_bayes import NaiveBayesClassifier
from ml.src.models.neural_network import NeuralNetworkClassifier
from ml.src.models.rnn import RNNClassifier
from ml.src.models.transformer import TransformerClassifier

# Registration is the only backend change needed when introducing a new implementation.
FACTORIES: dict[str, Callable[[], Classifier]] = {
    "naive_bayes": NaiveBayesClassifier,
    "neural_network": NeuralNetworkClassifier,
    "rnn": RNNClassifier,
    "attention": AttentionClassifier,
    "transformer": TransformerClassifier,
}
