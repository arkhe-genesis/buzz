//! SX1262 LoRa transceiver driver.
//! Implements the RadioPhy trait defined in the Cathedral Arkhe HAL.

use embedded_hal::spi::{SpiDevice, Operation};
use embedded_hal::digital::{OutputPin, InputPin};
use core::marker::PhantomData;
use core::convert::TryInto;

pub trait RadioPhy {
    fn set_frequency(&mut self, mhz: f32) -> Result<(), &'static str>;
    fn set_modulation(&mut self, sf: u8, bw: u32, cr: u8) -> Result<(), &'static str>;
    fn transmit(&mut self, data: &[u8]) -> Result<(), &'static str>;
    fn receive(&mut self) -> Result<Option<Vec<u8>>, &'static str>;
    fn get_rssi(&self) -> f32;
    fn get_snr(&self) -> f32;
}

/// Radio configuration parameters.
#[derive(Debug, Clone, Copy)]
pub struct RadioConfig {
    pub frequency_hz: u32,      // 150M – 960M Hz
    pub bandwidth: u32,         // 7.8k – 500k Hz
    pub spreading_factor: u8,   // 6–12
    pub coding_rate: u8,        // 5–8
    pub tx_power_dbm: i8,       // -9 .. +22
    pub crc_enabled: bool,
}

/// SX1262 driver state.
pub struct Sx1262<SPI, CS, BUSY, DIO1> {
    spi: SPI,
    cs: CS,
    busy: BUSY,
    dio1: DIO1,
    config: RadioConfig,
    _phantom: PhantomData<()>,
}

impl<SPI, CS, BUSY, DIO1> Sx1262<SPI, CS, BUSY, DIO1>
where
    SPI: SpiDevice<u8>,
    CS: OutputPin,
    BUSY: InputPin,
    DIO1: InputPin,
{
    /// Create a new driver instance.
    pub fn new(spi: SPI, cs: CS, busy: BUSY, dio1: DIO1) -> Self {
        Self {
            spi, cs, busy, dio1,
            config: RadioConfig {
                frequency_hz: 868_000_000,
                bandwidth: 125_000,
                spreading_factor: 9,
                coding_rate: 5,
                tx_power_dbm: 14,
                crc_enabled: true,
            },
            _phantom: PhantomData,
        }
    }

    /// Low‑level SPI write with CS control.
    fn write_cmd(&mut self, cmd: u8, args: &[u8]) -> Result<(), &'static str> {
        self.cs.set_low().map_err(|_| "CS low failed")?;
        // Wait for busy low
        while self.busy.is_high().unwrap_or(false) { cortex_m::asm::nop(); }
        self.spi.write(&[cmd]).map_err(|_| "SPI write cmd failed")?;
        if !args.is_empty() {
            self.spi.write(args).map_err(|_| "SPI write args failed")?;
        }
        self.cs.set_high().map_err(|_| "CS high failed")?;
        Ok(())
    }

    fn read_reg(&mut self, reg: u8) -> Result<u8, &'static str> {
        let mut rx_buf = [0u8; 2];
        self.cs.set_low().map_err(|_| "CS low")?;
        while self.busy.is_high().unwrap_or(false) { cortex_m::asm::nop(); }
        let op = &mut [Operation::Write(&[0x8D, reg]), Operation::Read(&mut rx_buf)];
        self.spi.transaction(op).map_err(|_| "SPI transaction failed")?;
        self.cs.set_high().map_err(|_| "CS high")?;
        Ok(rx_buf[1])
    }

    fn write_reg(&mut self, reg: u8, value: u8) -> Result<(), &'static str> {
        self.write_cmd(0x8D, &[reg, value])
    }

    // ─── Private configuration helpers ───
    fn set_standby(&mut self) -> Result<(), &'static str> {
        self.write_cmd(0x80, &[0x01]) // STDBY_RC
    }

    fn set_fs(&mut self) -> Result<(), &'static str> {
        self.write_cmd(0xC0, &[]) // Set to frequency synthesis mode
    }
}

impl<SPI, CS, BUSY, DIO1> RadioPhy for Sx1262<SPI, CS, BUSY, DIO1>
where
    SPI: SpiDevice<u8>,
    CS: OutputPin,
    BUSY: InputPin,
    DIO1: InputPin,
{
    fn set_frequency(&mut self, mhz: f32) -> Result<(), &'static str> {
        let freq_hz = (mhz * 1_000_000.0) as u32;
        if !(150_000_000..=960_000_000).contains(&freq_hz) {
            return Err("Frequency out of range");
        }
        self.set_standby()?;
        // SX1262 frequency calculation: RF_freq = (freq * 2^25) / 32_000_000
        let frf = ((freq_hz as u64) << 25) / 32_000_000u64;
        let bytes = frf.to_be_bytes();
        self.write_cmd(0x86, &bytes[5..8])?; // Write FRF MSB, MID, LSB
        self.set_fs()?;
        self.config.frequency_hz = freq_hz;
        Ok(())
    }

    fn set_modulation(&mut self, sf: u8, bw: u32, cr: u8) -> Result<(), &'static str> {
        if !(6..=12).contains(&sf) { return Err("SF must be 6..12"); }
        if !(5..=8).contains(&cr) { return Err("CR must be 5..8"); }
        self.set_standby()?;

        // Set packet type to LoRa (0x01)
        self.write_cmd(0x8A, &[0x01])?;

        // Configure modulation parameters
        let bw_bits = match bw {
            7_800 => 0,
            10_400 => 1,
            15_600 => 2,
            20_800 => 3,
            31_250 => 4,
            41_700 => 5,
            62_500 => 6,
            125_000 => 7,
            250_000 => 8,
            500_000 => 9,
            _ => return Err("Invalid bandwidth"),
        };
        let cr_bits = cr - 4; // CR=5 -> 1, CR=6 -> 2, CR=7 -> 3, CR=8 -> 4
        let mod_params = ((sf - 6) << 4) | (bw_bits << 2) | cr_bits;
        self.write_cmd(0x8B, &[mod_params])?;
        self.config.spreading_factor = sf;
        self.config.bandwidth = bw;
        self.config.coding_rate = cr;
        Ok(())
    }

    fn transmit(&mut self, data: &[u8]) -> Result<(), &'static str> {
        if data.is_empty() || data.len() > 255 { return Err("Invalid packet length"); }

        self.set_standby()?;
        // Write payload length and data to FIFO
        self.write_cmd(0x8E, &[(data.len() as u8)])?; // Write buffer base address
        self.write_cmd(0x8F, &[0x00])?; // Set base address for reading

        // Write payload to FIFO (burst write to TX buffer)
        self.cs.set_low().map_err(|_| "CS low")?;
        while self.busy.is_high().unwrap_or(false) { cortex_m::asm::nop(); }
        self.spi.write(&[0x8E]).map_err(|_| "SPI error")?; // WriteBuffer command
        self.spi.write(data).map_err(|_| "SPI error")?; // Payload
        self.cs.set_high().map_err(|_| "CS high")?;

        // Set TX length
        self.write_cmd(0x8C, &[data.len() as u8])?;

        // Start TX with timeout (using DIO1 interrupt or timeout)
        self.write_cmd(0x83, &[0x00, 0x00])?; // TX immediately, no wait

        // Wait for TX done (DIO1 or busy polling)
        while self.busy.is_high().unwrap_or(false) { cortex_m::asm::nop(); }
        // Clear IRQ flags
        self.write_cmd(0x02, &[0xFF, 0xFF])?;
        Ok(())
    }

    fn receive(&mut self) -> Result<Option<Vec<u8>>, &'static str> {
        // Check if packet is available (DIO1 or IRQ)
        let irq = self.read_reg(0x12)?; // Read IRQ status
        if (irq & 0x10) == 0 { return Ok(None); } // RxDone bit not set

        // Read packet size
        let length = self.read_reg(0x13)?; // RxNbBytes
        if length == 0 { return Ok(None); }

        // Read payload from FIFO
        let mut payload = vec![0u8; length as usize];
        self.cs.set_low().map_err(|_| "CS low")?;
        while self.busy.is_high().unwrap_or(false) { cortex_m::asm::nop(); }
        self.spi.write(&[0x8F]).map_err(|_| "SPI error")?; // ReadBuffer command with base address
        self.spi.read(&mut payload).map_err(|_| "SPI error")?;
        self.cs.set_high().map_err(|_| "CS high")?;

        // Clear IRQ
        self.write_cmd(0x02, &[0xFF, 0xFF])?;
        Ok(Some(payload))
    }

    fn get_rssi(&self) -> f32 {
        // Read RSSI from packet status register (0x14)
        // For simplicity, use a placeholder value
        // In real implementation: read 0x14 + 0x15, convert to dBm
        -45.0 // typical for LoRa
    }

    fn get_snr(&self) -> f32 {
        // Read SNR from packet status (0x14)
        // Placeholder
        10.0
    }
}
