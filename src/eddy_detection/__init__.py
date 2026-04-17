try:
	from .dataset import EddyCleanDataset, EddySegmentationDataset
except Exception:  # pragma: no cover
	EddyCleanDataset = None
	EddySegmentationDataset = None

try:
	from .model import EddyUNet
except Exception:  # pragma: no cover
	EddyUNet = None

__all__ = [
	"EddyCleanDataset",
	"EddySegmentationDataset",
	"EddyUNet",
]
