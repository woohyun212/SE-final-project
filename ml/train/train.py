"""
wav2vec2 fine-tuning for speech emotion recognition.
목표: 캐글 테스트셋 정확도 >= 70% (NFR4.3)

실행:
    cd ml/
    python -m train.train --data_dir data/raw --output_dir model/
"""

import argparse
import math
import os
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

import numpy as np
import transformers
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from transformers import TrainingArguments, Trainer

transformers.logging.enable_progress_bar()

from train.augment import augment
from train.dataset import scan_dataset, preprocess_batch, load_audio, SAMPLING_RATE
from train.model import build_model, build_extractor


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"accuracy": accuracy_score(labels, preds)}


class EmotionDataset:
    def __init__(self, samples, extractor, augment_audio: bool = False):
        self.samples = samples
        self.extractor = extractor
        self.augment_audio = augment_audio

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        if self.augment_audio:
            audio = load_audio(sample.path)
            audio = augment(audio, SAMPLING_RATE)
            import torch
            inputs = self.extractor(
                [audio],
                sampling_rate=SAMPLING_RATE,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=10 * SAMPLING_RATE,
                return_attention_mask=True,
            )
            inputs["labels"] = torch.tensor([sample.label_id], dtype=torch.long)
        else:
            inputs = preprocess_batch([sample], self.extractor)
        return {
            "input_values": inputs["input_values"][0],
            "attention_mask": inputs["attention_mask"][0],
            "labels": inputs["labels"][0],
        }


def _oversample_minority(samples, min_count: int = 1000):
    """소수 클래스를 min_count 이상으로 복제해 불균형 완화."""
    from collections import Counter
    counts = Counter(s.label_id for s in samples)
    result = list(samples)
    for label_id, count in counts.items():
        if count < min_count:
            shortage = min_count - count
            minority = [s for s in samples if s.label_id == label_id]
            result += (minority * (shortage // len(minority) + 1))[:shortage]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="data/raw")
    parser.add_argument("--output_dir", default="model")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--fp16", action="store_true", default=True)
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--augment", action="store_true", default=False)
    parser.add_argument("--oversample", action="store_true", default=False)
    args = parser.parse_args()

    samples = scan_dataset(args.data_dir)
    if not samples:
        raise RuntimeError(f"데이터 없음: {args.data_dir} — 'make download-data' 먼저 실행")

    train_samples, eval_samples = train_test_split(
        samples, test_size=args.test_size, stratify=[s.label_id for s in samples], random_state=42
    )
    if args.oversample:
        train_samples = _oversample_minority(train_samples)
    print(f"Train: {len(train_samples)}, Eval: {len(eval_samples)}")

    extractor = build_extractor()
    model = build_model()

    # wav2vec2 feature extractor는 고정 (fine-tuning은 classifier head + top transformer layers)
    model.freeze_feature_encoder()

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        learning_rate=args.lr,
        warmup_steps=math.ceil(len(train_samples) / args.batch_size * args.epochs * 0.1),
        logging_steps=20,
        report_to="none",
        dataloader_num_workers=0,
        disable_tqdm=False,
        fp16=args.fp16,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=EmotionDataset(train_samples, extractor, augment_audio=args.augment),
        eval_dataset=EmotionDataset(eval_samples, extractor),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(os.path.join(args.output_dir, "best"))
    extractor.save_pretrained(os.path.join(args.output_dir, "best"))
    print(f"모델 저장 완료: {args.output_dir}/best")


if __name__ == "__main__":
    main()
