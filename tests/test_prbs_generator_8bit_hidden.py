import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.load.value = 0
    dut.prbs_type.value = 0
    dut.seed.value = 0

    await Timer(20, unit="ns")

    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    assert dut.prbs_out.value == 0, \
        f"Reset failed. Expected 0 Got {dut.prbs_out.value}"


@cocotb.test()
async def test_seed_load(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    seed = 0x12345679

    dut.seed.value = seed
    dut.load.value = 1

    await RisingEdge(dut.clk)

    dut.load.value = 0

    await Timer(1, unit="ns")

    expected = seed & 0xFF

    assert dut.prbs_out.value == expected, \
        f"Seed load failed. Expected {hex(expected)} Got {hex(int(dut.prbs_out.value))}"


@cocotb.test()
async def test_hold_when_disabled(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    dut.seed.value = 0xABCDEF13
    dut.load.value = 1

    await RisingEdge(dut.clk)

    dut.load.value = 0

    await Timer(1, unit="ns")

    value_before = int(dut.prbs_out.value)

    dut.enable.value = 0

    for _ in range(6):
        await RisingEdge(dut.clk)

    value_after = int(dut.prbs_out.value)

    assert value_before == value_after, \
        "Output changed when disabled (enable=0)"


@cocotb.test()
async def test_prbs_modes(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    seed = 0xDEADBEF0

    dut.seed.value = seed
    dut.load.value = 1

    await RisingEdge(dut.clk)

    dut.load.value = 0

    dut.enable.value = 1

    for mode in [0, 1, 2, 3]:

        dut.prbs_type.value = mode

        prev_val = int(dut.prbs_out.value)

        await RisingEdge(dut.clk)

        new_val = int(dut.prbs_out.value)

        assert prev_val != new_val, \
            f"PRBS mode {mode} did not update output"


@cocotb.test()
async def test_multiple_cycles(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset_dut(dut)

    dut.seed.value = 0xCAFEBABF
    dut.load.value = 1

    await RisingEdge(dut.clk)

    dut.load.value = 0
    dut.enable.value = 1
    dut.prbs_type.value = 1

    outputs = []

    for _ in range(21):
        await RisingEdge(dut.clk)
        outputs.append(int(dut.prbs_out.value))

    assert len(set(outputs)) > 2, \
        "PRBS output not changing across cycles"

def test_simple_dff_hidden_runner():
   sim = os.getenv("SIM", "icarus")

   proj_path = Path(__file__).resolve().parent.parent

   sources = [proj_path / "sources/prbs_generator_8bit.sv"]

   runner = get_runner(sim)
   runner.build(
       sources=sources,
       hdl_toplevel="prbs_generator_8bit",
       always=True,
   )

   runner.test(hdl_toplevel="prbs_generator_8bit", test_module="test_prbs_generator_8bit_hidden")
