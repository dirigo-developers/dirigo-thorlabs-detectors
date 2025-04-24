import serial
import pyvisa

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
        raise NotImplementedError("PDA40 SiPMs cannot be enabled/disabled in software.")
    
    @property
    def gain(self):
        """Switchable gain; raise NotImplementedError if fixed."""
        raise NotImplementedError("Gain can not be reported with PDA40 SiPMs")

    @gain.setter
    def gain(self, value) -> None: 
        raise NotImplementedError("Gain is not adjustable with PDA40 SiPMs")
    
    @property
    def gain_range(self):
        return units.ValueRange(min=0, max=9) # manually set positions

    @property
    def bandwidth(self) -> units.Frequency: 
        """Switchable bandwidth; raise NotImplementedError if fixed."""
        return units.Frequency("100 MHz") # 3dB cutoff for the measured ~4.5 ns pulse assuming Gaussian pulse shape

    @bandwidth.setter
    def bandwidth(self, value: units.Frequency):
        raise NotImplementedError("Bandwidth is not adjustable with PDA40 SiPMs")



class PMT2100(Detector):
    """
    Thorlabs PMT2101 controller via SCPI over USB.

    Requires Keysight VISA-compatible driver so the device
    appears as a serial port.
    """

    def __init__(
        self,
        serial_number: int,
        timeout: float = units.Time("1 s"),
        **kwargs
    ) -> None:
        super().__init__()
        
        rm = pyvisa.ResourceManager()        # Uses the system VISA (Keysight/NI)
        
        self._res = rm.open_resource(f"USB0::0x1313::0x2F00::{serial_number}::0::INSTR")
        self._res.timeout = int(1000*timeout)
        #print(pmt.query("*IDN?"))

        self._sensor = self._res.query("SENS:DET?") # returns the sensor name, e.g. 'H10721'

        self._index = -1  # will be set by DetectorSet

    def close(self) -> None:
        """Close the serial port when done."""
        self._res.close()

    # ------------------------------------------------------ Detector API
    @property
    def enabled(self) -> bool:
        """Turns the PMT high-voltage on/off."""
        resp = self._res.query(f"SENS:FUNC:STAT? {self._sensor}")
        # device returns "1" for on, "0" for off
        print(resp)
        return resp == "1"

    @enabled.setter
    def enabled(self, state: bool) -> None:
        if state:
            cmd = f"SENS:FUNC:ON {self._sensor}"  
        else:
            cmd = f"SENS:FUNC:OFF {self._sensor}"
        self._res.write(cmd)

    # TODO, add offset, bias

    @property
    def gain(self) -> units.Voltage:
        """
        PMT gain (really the gain control voltage) in volts.
        """
        self._res.write("INST:SEL GAIN")
        resp = self._res.query(":SOUR:VOLT:LEV:IMM:AMPL?")
        return units.Voltage(resp)

    @gain.setter
    def gain(self, value) -> None:
        if not self.gain_range.within_range(value):
            l, h = self.gain_range.min, self.gain_range.max
            raise ValueError(f"Gain voltage must be between {l} and {h}")
        self._res.write("INST:SEL GAIN")
        self._res.write(f":SOUR:VOLT:LEV:IMM:AMPL {float(value)}")

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
        return self._res.query("*IDN?")

    def status_byte(self) -> int:
        """Read the 488.2 status byte."""
        resp = self._res.query("*STB?")
        return int(resp)