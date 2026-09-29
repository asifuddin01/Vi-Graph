"""Batching for training: the processor's chat template, loss on the answer only.

Labels copy the input ids, with every token up to and including the assistant header (the
template's generation prompt, e.g. ``<|im_start|>assistant\\n``) set to -100, so the loss
covers the answer JSON and the end-of-turn token only. The header is derived from the
model's own template, not hard-coded. One example per batch: images differ in size, and a
T4 fits one at a time anyway (micro_batch_size 1 + gradient accumulation).
"""

from __future__ import annotations

from typing import Any

from training.qlora.data import Example

IGNORE_INDEX = -100


class LabelMaskError(ValueError):
    pass


def mask_prompt(ids: list[int], header: list[int]) -> list[int]:
    """Labels for ``ids``: -100 up to and including the last occurrence of ``header``."""
    size = len(header)
    for start in range(len(ids) - size, -1, -1):
        if ids[start : start + size] == header:
            end = start + size
            if end == len(ids):
                raise LabelMaskError("nothing after the assistant header to learn")
            return [IGNORE_INDEX] * end + ids[end:]
    raise LabelMaskError("assistant header not found in the tokenized conversation")


def assistant_header(processor: Any) -> list[int]:
    """Token ids the chat template adds before an assistant answer."""
    conversation = [{"role": "user", "content": [{"type": "text", "text": "x"}]}]
    with_prompt = processor.apply_chat_template(conversation, add_generation_prompt=True)
    without = processor.apply_chat_template(conversation, add_generation_prompt=False)
    if not with_prompt.startswith(without) or with_prompt == without:
        raise LabelMaskError("cannot derive the assistant header from the chat template")
    header_text = with_prompt[len(without) :]
    return list(processor.tokenizer(header_text, add_special_tokens=False)["input_ids"])


def flat_ids(input_ids: Any) -> list[int]:
    """input_ids of one conversation as a flat list (tensor, nested list or list)."""
    values = input_ids.tolist() if hasattr(input_ids, "tolist") else list(input_ids)
    if values and isinstance(values[0], list):
        if len(values) != 1:
            raise ValueError("expected one conversation")
        values = values[0]
    return values


class Collator:
    def __init__(self, processor: Any) -> None:
        self.processor = processor
        self.header = assistant_header(processor)

    def __call__(self, examples: list[Example]) -> dict[str, Any]:
        if len(examples) != 1:
            raise ValueError("micro_batch_size must be 1")
        import torch

        batch = self.processor.apply_chat_template(
            examples[0].conversation,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        labels = mask_prompt(flat_ids(batch["input_ids"]), self.header)
        batch["labels"] = torch.tensor([labels], dtype=torch.long)
        return dict(batch)

    def trained_text(self, example: Example) -> str:
        """The decoded tokens the loss covers — shown by the smoke run as a sanity check."""
        batch = self.processor.apply_chat_template(
            example.conversation, tokenize=True, return_dict=True
        )
        labels = mask_prompt(flat_ids(batch["input_ids"]), self.header)
        return self.processor.tokenizer.decode([t for t in labels if t != IGNORE_INDEX])
