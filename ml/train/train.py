"""
wav2vec2 fine-tuning for speech emotion recognition.
목표: 캐글 테스트셋 정확도 >= 70% (NFR4.3)

실행:
    cd ml/
    python -m train.train --data_dir data/raw --output_dir model/
"""

import argparse
import os

import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from transformers import TrainingArguments, Trainer

from train.dataset import scan_dataset, preprocess_batch
from train.model import build_model, build_extractor


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"accuracy": accuracy_score(labels, preds)}


class EmotionDataset:
    def __init__(self, samples, extractor):
        self.samples = samples
        self.extractor = extractor

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        batch = preprocess_batch([self.samples[idx]], self.extractor)
        return {
            "input_values": batch["input_values"][0],
            "attention_mask": batch["attention_mask"][0],
            "labels": batch["labels"][0],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="data/raw")
    parser.add_argument("--output_dir", default="model")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--test_size", type=float, default=0.2)
    args = parser.parse_args()

    samples = scan_dataset(args.data_dir)
    if not samples:
        raise RuntimeError(f"데이터 없음: {args.data_dir} — 'make download-data' 먼저 실행")

    train_samples, eval_samples = train_test_split(
        samples, test_size=args.test_size, stratify=[s.label_id for s in samples], random_state=42
    )
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
        warmup_ratio=0.1,
        logging_steps=20,
        report_to="none",
        dataloader_num_workers=2,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=EmotionDataset(train_samples, extractor),
        eval_dataset=EmotionDataset(eval_samples, extractor),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(os.path.join(args.output_dir, "best"))
    extractor.save_pretrained(os.path.join(args.output_dir, "best"))
    print(f"모델 저장 완료: {args.output_dir}/best")


if __name__ == "__main__":
    main()
