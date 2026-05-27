from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

from train.dataset import EMOTION_LABELS, LABEL2ID, ID2LABEL

BASE_MODEL = "facebook/wav2vec2-base"


def build_model() -> Wav2Vec2ForSequenceClassification:
    return Wav2Vec2ForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(EMOTION_LABELS),
        label2id=LABEL2ID,
        id2label=ID2LABEL,
    )


def build_extractor() -> Wav2Vec2FeatureExtractor:
    return Wav2Vec2FeatureExtractor.from_pretrained(BASE_MODEL)
