"""Label vocabularies for synthetic diagrams, per diagram type and node role.

Each role has fixed labels plus templates with random parameters, so even large (L4) graphs
get realistic, mostly unique labels. ``LabelSource`` draws without replacement and falls
back to templates when the fixed labels run out.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# role → (fixed labels, templates); templates use {k} {c} {n} {p} {i} {x} placeholders.
Vocabulary = dict[str, tuple[list[str], list[str]]]

NEURAL_NETWORK: Vocabulary = {
    "source": (
        ["Input Image", "Tokens", "Input", "Audio Waveform", "Point Cloud", "Text"],
        ["Input {i}"],
    ),
    "step": (
        [
            "Conv 3x3",
            "Conv 1x1",
            "Conv 5x5",
            "Linear",
            "Embedding",
            "LSTM",
            "GRU",
            "Encoder",
            "Decoder",
            "Transformer Block",
            "Multi-Head Attention",
            "Self-Attention",
            "Feed Forward",
            "Patch Embedding",
            "Positional Encoding",
            "Residual Block",
            "Bottleneck",
            "Depthwise Conv",
            "Upsample",
            "Downsample",
            "CNN Encoder",
            "Transformer Encoder",
            "Projection Head",
            "Cross-Attention",
            "MLP",
        ],
        [
            "Conv {k}x{k}, {c}",
            "Linear {n}",
            "Block {i}",
            "Stage {i}",
            "Encoder Layer {i}",
            "Decoder Layer {i}",
            "Attention Head {i}",
        ],
    ),
    "op": (
        [
            "ReLU",
            "GELU",
            "BatchNorm",
            "Layer Norm",
            "Dropout",
            "Max Pool",
            "Avg Pool",
            "Global Avg Pool",
            "Flatten",
            "Softmax",
            "Sigmoid",
            "Tanh",
        ],
        ["Dropout {p}", "Pool {k}x{k}"],
    ),
    "fusion": (["Concat", "Add", "Feature Fusion", "Merge", "Sum", "Gated Fusion"], ["Fusion {i}"]),
    "decision": (["Early Exit?", "Confidence > 0.9?"], ["Gate {i}?"]),
    "sink": (
        ["Classifier", "Output", "Logits", "Class Scores", "Bounding Boxes", "Mask", "Prediction"],
        ["Head {i}"],
    ),
    "group": (
        [
            "Encoder Block",
            "Decoder Block",
            "Residual Block",
            "Backbone",
            "Neck",
            "Attention Module",
        ],
        ["Stage {i}", "Block {i}"],
    ),
}

FLOWCHART: Vocabulary = {
    "source": (["Start", "Begin", "Receive Request"], ["Start {i}"]),
    "step": (
        [
            "Read Input",
            "Validate Data",
            "Process Record",
            "Save Result",
            "Send Email",
            "Log Error",
            "Update Database",
            "Notify User",
            "Check Inventory",
            "Charge Card",
            "Generate Report",
            "Load Config",
            "Parse File",
            "Compute Total",
            "Apply Discount",
        ],
        ["Step {i}", "Task {i}", "Process Batch {i}", "Handle Case {i}"],
    ),
    "op": (["Increment Counter", "Wait", "Sleep 5s", "Reset Flag"], ["Set x = {n}"]),
    "fusion": (["Continue", "Join", "Merge Results"], ["Join {i}"]),
    "decision": (
        ["Is Valid?", "Retry?", "In Stock?", "Approved?", "x > 0?", "Done?", "Error?"],
        ["Condition {i}?", "Check {i}?"],
    ),
    "sink": (["End", "Stop", "Return Result", "Exit"], ["End {i}"]),
    "group": (["Validation", "Payment", "Error Handling", "Main Loop"], ["Phase {i}"]),
}

DATA_PIPELINE: Vocabulary = {
    "source": (
        ["Raw Events", "Kafka Topic", "S3 Bucket", "Clickstream", "IoT Sensors", "Postgres CDC"],
        ["Source {i}"],
    ),
    "step": (
        [
            "Ingest",
            "Clean",
            "Deduplicate",
            "Join",
            "Aggregate",
            "Enrich",
            "Validate Schema",
            "Filter",
            "Normalize",
            "Partition",
            "Transform",
            "Sessionize",
            "Spark Job",
            "Airflow DAG",
            "dbt Model",
        ],
        ["Transform {i}", "Job {i}", "Stage {i}"],
    ),
    "op": (["Cast Types", "Drop Nulls", "Hash IDs", "Sort"], ["Window {n}m"]),
    "fusion": (["Union", "Join Streams", "Merge"], ["Union {i}"]),
    "decision": (["Schema OK?", "Late Data?"], ["Quality Gate {i}?"]),
    "sink": (
        ["Data Warehouse", "Feature Store", "Dashboard", "Data Lake", "BI Report", "Search Index"],
        ["Sink {i}"],
    ),
    "group": (["Bronze Layer", "Silver Layer", "Gold Layer", "Streaming", "Batch"], ["Zone {i}"]),
}

ML_PIPELINE: Vocabulary = {
    "source": (["Dataset", "Raw Images", "Labels", "Training Data"], ["Dataset {i}"]),
    "step": (
        [
            "Preprocess",
            "Augment",
            "Split",
            "Train",
            "Validate",
            "Evaluate",
            "Tune",
            "Hyperparameter Search",
            "Feature Extraction",
            "Model Selection",
            "Cross-Validation",
            "Distill",
            "Quantize",
            "Export ONNX",
            "Fine-tune",
        ],
        ["Experiment {i}", "Train Model {i}", "Fold {i}"],
    ),
    "op": (["Resize", "Normalize", "Shuffle", "Tokenize"], ["Crop {n}px"]),
    "fusion": (["Ensemble", "Combine Features", "Merge Splits"], ["Ensemble {i}"]),
    "decision": (["Accuracy > 90%?", "Converged?", "Drift?"], ["Threshold {i}?"]),
    "sink": (["Model Registry", "Deploy", "Monitor", "Report", "Predictions"], ["Artifact {i}"]),
    "group": (["Data Prep", "Training", "Evaluation", "Serving"], ["Stage {i}"]),
}

SCIENTIFIC_WORKFLOW: Vocabulary = {
    "source": (["Sample Collection", "Raw Reads", "Sensor Data", "Survey Data"], ["Batch {i}"]),
    "step": (
        [
            "Sequencing",
            "Quality Control",
            "Alignment",
            "Variant Calling",
            "Annotation",
            "Normalization",
            "Statistical Analysis",
            "Clustering",
            "Peak Detection",
            "Imputation",
            "Simulation",
            "Calibration",
            "Segmentation",
        ],
        ["Analysis {i}", "Run {i}", "Replicate {i}"],
    ),
    "op": (["Trim Adapters", "Filter Low Quality", "Log Transform"], ["Bin {n}"]),
    "fusion": (["Merge Replicates", "Combine Results", "Meta-analysis"], ["Pool {i}"]),
    "decision": (["QC Passed?", "p < 0.05?"], ["Criterion {i}?"]),
    "sink": (["Visualization", "Report", "Publication Figure", "Results Table"], ["Output {i}"]),
    "group": (["Preprocessing", "Analysis", "Validation"], ["Module {i}"]),
}

SYSTEM_ARCHITECTURE: Vocabulary = {
    "source": (["Client", "Web Browser", "Mobile App", "Admin Console"], ["Client {i}"]),
    "step": (
        [
            "Load Balancer",
            "API Gateway",
            "Auth Service",
            "User Service",
            "Order Service",
            "Payment Service",
            "Search Service",
            "Notification Service",
            "Worker",
            "Scheduler",
            "Rate Limiter",
            "Reverse Proxy",
            "GraphQL Server",
        ],
        ["Service {i}", "Worker {i}", "Replica {i}"],
    ),
    "op": (["Cache", "Queue", "Circuit Breaker"], ["Shard {i}"]),
    "fusion": (["Aggregator", "Message Bus", "Event Router"], ["Bus {i}"]),
    "decision": (["Authorized?", "Cache Hit?"], ["Route {i}?"]),
    "sink": (
        ["Database", "Object Storage", "Data Warehouse", "Email Provider", "Logs", "Metrics"],
        ["Store {i}"],
    ),
    "group": (["Backend", "Frontend", "Data Layer", "VPC", "Kubernetes Cluster"], ["Zone {i}"]),
}

UML_CLASSES = [
    "User",
    "Account",
    "Order",
    "OrderItem",
    "Product",
    "Category",
    "Payment",
    "Invoice",
    "Customer",
    "Address",
    "Shipment",
    "Warehouse",
    "Supplier",
    "Review",
    "Cart",
    "Coupon",
    "Employee",
    "Manager",
    "Department",
    "Session",
    "Notification",
    "Admin",
    "Guest",
    "CreditCard",
    "BankTransfer",
    "Vehicle",
    "Car",
    "Truck",
    "Engine",
    "Wheel",
    "Shape",
    "Circle",
    "Rectangle",
    "Animal",
    "Dog",
    "Cat",
    "Repository",
    "Service",
    "Controller",
    "Logger",
]

VOCABULARIES: dict[str, Vocabulary] = {
    "neural_network": NEURAL_NETWORK,
    "flowchart": FLOWCHART,
    "data_pipeline": DATA_PIPELINE,
    "ml_pipeline": ML_PIPELINE,
    "scientific_workflow": SCIENTIFIC_WORKFLOW,
    "system_architecture": SYSTEM_ARCHITECTURE,
}

EDGE_LABELS = {
    "data_pipeline": ["events", "batch", "stream", "hourly", "parquet"],
    "system_architecture": ["HTTP", "gRPC", "SQL", "pub/sub", "REST", "WebSocket"],
    "ml_pipeline": ["train", "val", "test", "metrics"],
    "scientific_workflow": ["FASTQ", "BAM", "VCF", "CSV"],
}


@dataclass
class LabelSource:
    """Draws labels for one graph: fixed labels first, then templates; mostly unique."""

    rng: random.Random
    vocabulary: Vocabulary
    used: set[str] = field(default_factory=set)
    _counters: dict[str, int] = field(default_factory=dict)

    def draw(self, role: str) -> str:
        fixed, templates = self.vocabulary[role]
        fresh = [label for label in fixed if label not in self.used]
        if fresh and self.rng.random() < 0.85:
            label = self.rng.choice(fresh)
        else:
            label = self._from_template(role, templates)
        self.used.add(label)
        return label

    def _from_template(self, role: str, templates: list[str]) -> str:
        for _ in range(20):
            index = self._counters.get(role, 0) + 1
            self._counters[role] = index
            label = self.rng.choice(templates).format(
                i=index,
                k=self.rng.choice([1, 3, 5, 7]),
                c=self.rng.choice([32, 64, 128, 256, 512]),
                n=self.rng.choice([16, 64, 128, 256, 512, 1024]),
                p=self.rng.choice([0.1, 0.2, 0.3, 0.5]),
                x=self.rng.randint(1, 9),
            )
            if label not in self.used:
                return label
        return f"{role.title()} {len(self.used) + 1}"
