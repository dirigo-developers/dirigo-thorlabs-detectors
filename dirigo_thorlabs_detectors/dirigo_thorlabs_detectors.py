import serial

from dirigo import units
from dirigo.hw_interfaces.detector import Detector



class PDA40(Detector):
    """Thorlabs PDA40-series Silicon Photomultiplier Modules."""
    def __init__(self, model: str, **kwargs):
        super().__init__()
        self._model = model

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
    def gain_range(self):
        return units.ValueRange(min=0, max=9) # manually set positions

    @property
    def bandwidth(self) -> units.Frequency: 
        """Switchable bandwidth; raise NotImplementedError if fixed."""
        return units.Frequency("100 MHz") # 3dB cutoff for the measured ~4.5 ns pulse assuming Gaussian pulse shape

    @bandwidth.setter
    def bandwidth(self, value: units.Frequency):
        raise NotImplementedError("Bandwidth is not adjustable with PDA4X SiPMs")



class PMT2100:
    """
    Thorlabs PMT2101 controller via SCPI over USB.

    Requires Keysight VISA-compatible driver so the device
    appears as a serial port.
    """

    def __init__(
        self,
        com_port: int,
        baudrate: int = 115200,
        timeout: float = 1.0,
    ) -> None:
        super().__init__()
        self._ser = serial.Serial("COM" + str(com_port), baudrate, timeout=timeout)
        #self._logger = logging.getLogger(f"{self.__class__.__name__}[{port}]")
        self._index = -1  # will be set by DetectorSet

    def _write(self, cmd: str) -> None:
        full_cmd = cmd.strip() + "\n"
        #self._logger.debug("→ %s", full_cmd.strip())
        self._ser.write(full_cmd.encode("ascii"))

    def _query(self, cmd: str) -> str:
        self._write(cmd)
        resp = self._ser.readline().decode("ascii", errors="ignore").strip()
        #self._logger.debug("← %s", resp)
        return resp
    
    def _select(self, channel: str) -> None:
        self._write(f":SELect {channel}")

    def close(self) -> None:
        """Close the serial port when done."""
        self._ser.close()

    # ------------------------------------------------------ Detector API
    @property
    def enabled(self) -> bool:
        """Turns the PMT high-voltage on/off."""
        resp = self._query(":FUNCtion:STATe? PMT")
        # device returns "1" for on, "0" for off
        return resp == "1"

    @enabled.setter
    def enabled(self, state: bool) -> None:
        cmd = ":FUNCtion:ON PMT" if state else ":FUNCtion:OFF PMT"
        self._write(cmd)

    # TODO, add offset, bias

    @property
    def gain(self) -> units.Voltage:
        """
        PMT gain (really the gain control voltage) in volts.
        """
        self._select("GAIN")
        resp = self._query(":VOLTage:LEVel:IMMediate:AMPlitude?")
        return units.Voltage(resp)

    @gain.setter
    def gain(self, value) -> None:
        if not self.gain_range.within_range(value):          # adjust limit if needed
            l, h = self.gain_range.min, self.gain_range.max
            raise ValueError(f"Gain voltage must be between {l} and {h}")
        self._select("GAIN")
        self._write(f":VOLTage:LEVel:IMMediate:AMPlitude {float(value)}")

    @property
    def gain_range(self) -> units.VoltageRange:
        return units.VoltageRange(min="0.5 V", max="1 V")

    @property
    def bandwidth(self) -> units.Frequency:
        """
        Low-pass filter corner frequency.
        Supported values: 80, 2.5, 0.25 MHz
        """
        resp = self._query(":SENSe:FILTer:LPASs:FREQuency?")
        return units.Frequency(resp)

    @bandwidth.setter
    def bandwidth(self, freq: units.Frequency) -> None:
        if freq not in (units.Frequency("80 MHz"), units.Frequency("2.5 MHz"), units.Frequency("0.25 MHz")):
            raise ValueError("Bandwidth must be one of: 80, 2.5, 0.25 (MHz)")
        self._write(f":SENSe:FILTer:LPASs:FREQuency {freq}")

    # ---------------------------------------------------- Optional helpers
    def identify(self) -> str:
        """Query the instrument identity string."""
        return self._query("*IDN?")

    def status_byte(self) -> int:
        """Read the 488.2 status byte."""
        resp = self._query("*STB?")
        return int(resp)