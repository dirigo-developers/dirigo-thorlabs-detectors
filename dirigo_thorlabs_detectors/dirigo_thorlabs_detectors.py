from dirigo import units
from dirigo.hw_interfaces.detector import Detector


class PDA4X(Detector):

    def __init__(self, model_number: str, **kwargs):
        super().__init__()
        self._model = model_number

    @property
    def enabled(self) -> bool:
        return True # If On, then always enabled (no software switching)
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        raise NotImplementedError("PDA4X SiPMs cannot be enabled/disabled in software.")
    
    @property
    def gain(self):
        """Switchable gain; raise NotImplementedError if fixed."""
        raise NotImplementedError("PDA4X SiPMs cannot report current gain.")

    @gain.setter
    def gain(self, value) -> None: 
        raise NotImplementedError("PDA4X SiPMs cannot adjust gain in software.")

    @property
    def bandwidth(self) -> units.Frequency: 
        """Switchable bandwidth; raise NotImplementedError if fixed."""
        return units.Frequency("100 MHz") # 3dB cutoff for the measured ~4.5 ns pulse assuming Gaussian pulse shape

    @bandwidth.setter
    def bandwidth(self, value: units.Frequency):
        raise NotImplementedError("Bandwidth is not adjustable with PDA4X SiPMs")