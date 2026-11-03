"""Transcript tests: replay the spec's sample sessions through the real menu
and compare the output line by line."""

from pathlib import Path

import pytest

from main import Console, main

DATA_DIR = Path(__file__).parent.parent / "data"

SAMPLES = """
# startup
Loaded 7 items, 5 customers, 10 rentals, 4 fines.
Today is 2026-11-03.
=== GearShare Mini ===
1. List catalogue
2. Search by name or tag
3. Rent
4. Return
5. Extend
6. Join waiting list
7. Customer rentals
8. Overdue report
0. Exit
> abc
Please enter a number from 0 to 8.
>
Please enter a number from 0 to 8.
> 0

# catalogue
> 1
SKU         NAME                      TYPE       AVAILABLE
1000000001  Canon EOS 200D            Equipment  1 of 2
1000000002  Sony 50mm Lens            Equipment  1 of 1
1000000003  DJI Mini Drone            Equipment  0 of 1
1000000004  Manfrotto Tripod          Equipment  1 of 2
1000000005  Rode Wireless Mic         Equipment  1 of 1
1000000006  Vintage Leica (Showcase)  Display    not rentable
1000000007  SD Card 128GB             Accessory  3 of 3
> 0

# search
> 2
Search: VIDEO
1 result:
1000000003  DJI Mini Drone  (video, aerial)  0 of 1
> 2
Search: zzz
No items match 'zzz'.
> 0

# session_a
> 3
Customer ID: C001
SKU: 1000000002
OK: Ananya Nair rented 'Sony 50mm Lens'. Due 2026-11-06.
> 3
Customer ID: C001
SKU: 1000000002
ERROR [R8]: Ananya Nair already has a unit of 'Sony 50mm Lens'.
> 3
Customer ID: C003
SKU: 1000000006
ERROR [R1]: 'Vintage Leica (Showcase)' is a display item and cannot be rented.
> 3
Customer ID: C004
SKU: 1000000004
ERROR [R4]: Rohan Das has unpaid fines of ₹600 (limit ₹500).
> 3
Customer ID: C003
SKU: 1000000003
No units of 'DJI Mini Drone' are available. Join the waiting list? (y/n): y
OK: Meera Joshi is #1 on the waiting list for 'DJI Mini Drone'.
> 4
Rental ID: RN001
OK: Vikram Shah returned 'DJI Mini Drone'. Late by 5 days. Fee: ₹500.
Next on waiting list: Meera Joshi.
> 0

# other_errors
> 3
Customer ID: C009
ERROR [CustomerNotFoundError]: No customer with ID C009.
> 3
Customer ID: C001
SKU: 123
ERROR [InvalidSKUError]: SKU must be exactly 10 digits.
> 3
Customer ID: C001
SKU: 1000000999
ERROR [ItemNotFoundError]: No item with SKU 1000000999.
> 3
Customer ID: C001
SKU: 1000000002
OK: Ananya Nair rented 'Sony 50mm Lens'. Due 2026-11-06.
> 3
Customer ID: C001
SKU: 1000000007
OK: Ananya Nair rented 'SD Card 128GB'. Due 2026-11-05.
> 3
Customer ID: C001
SKU: 1000000004
ERROR [R3]: Ananya Nair already has 2 of 2 items on rental.
> 0

# return_on_time
> 4
Rental ID: RN003
OK: Meera Joshi returned 'Manfrotto Tripod'. Returned on time. Fee: ₹0.
> 0

# extensions
> 3
Customer ID: C001
SKU: 1000000007
OK: Ananya Nair rented 'SD Card 128GB'. Due 2026-11-05.
> 5
Rental ID: RN003
OK: Extended 'Manfrotto Tripod' (extension 1 of 2). New due date 2026-11-13.
> 5
Rental ID: RN003
OK: Extended 'Manfrotto Tripod' (extension 2 of 2). New due date 2026-11-20.
> 5
Rental ID: RN003
ERROR [R6]: 'Manfrotto Tripod' has already been extended 2 times.
> 5
Rental ID: RN011
ERROR [R2]: Accessories cannot be extended.
> 0

# extension_waiting
> 3
Customer ID: C001
SKU: 1000000004
OK: Ananya Nair rented 'Manfrotto Tripod'. Due 2026-11-06.
> 6
Customer ID: C005
SKU: 1000000004
OK: Pooja Menon is #1 on the waiting list for 'Manfrotto Tripod'.
> 5
Rental ID: RN003
ERROR [R6]: 'Manfrotto Tripod' cannot be extended because another customer is waiting.
> 0

# customer_rentals
> 7
Customer ID: C002
Rentals for Vikram Shah (Plus: 4 items, 5 days, ₹100/day)
RENTAL  ITEM            ISSUED      DUE         STATUS
RN001   DJI Mini Drone  2026-10-24  2026-10-29  OVERDUE (5 days)
Active rentals: 1 of 4
Unpaid fines: ₹0
> 0

# overdue_report
> 8
Overdue rentals as of 2026-11-03
RENTAL  CUSTOMER     ITEM            DUE         DAYS  FINE SO FAR
RN001   Vikram Shah  DJI Mini Drone  2026-10-29     5  ₹500
RN002   Rohan Das    Canon EOS 200D  2026-10-31     3  ₹150
Total overdue: 2   Fines so far: ₹650
> 0
"""


def parse_samples(text):
    """Split SAMPLES into {name: [expected lines]}."""
    samples, name = {}, None
    for line in text.strip().splitlines():
        if line.startswith("# "):
            name = line[2:]
            samples[name] = []
        elif line:
            samples[name].append(line)
    return samples


def answers_from(lines):
    """Pull what the user typed out of the transcript (text after the prompt)."""
    prompts = ("> ", "Customer ID: ", "SKU: ", "Rental ID: ", "Search: ", "(y/n): ")
    answers = []
    for line in lines:
        if line == ">":
            answers.append("")
            continue
        for prompt in prompts:
            if prompt in line and (line.startswith(prompt) or prompt == "(y/n): "):
                answers.append(line.split(prompt, 1)[1])
                break
    return answers


def make_reader(answers):
    """A fake input(): prints prompt + answer, like a terminal echoing typing."""
    feed = iter(answers)

    def read(prompt):
        answer = next(feed)
        print(f"{prompt}{answer}")
        return answer
    return read


def output_lines(capsys):
    return [line.rstrip() for line in capsys.readouterr().out.splitlines()]


SAMPLE_SESSIONS = parse_samples(SAMPLES)


def test_startup_and_bad_menu_input(capsys):
    expected = SAMPLE_SESSIONS["startup"]
    main(read=make_reader(answers_from(expected)), env={"TODAY": "2026-11-03"},
         data_dir=DATA_DIR)
    assert output_lines(capsys) == expected


@pytest.mark.parametrize("name", [n for n in SAMPLE_SESSIONS if n != "startup"])
def test_sample_transcript(name, shop, today, capsys):
    expected = SAMPLE_SESSIONS[name]
    Console(shop, today, make_reader(answers_from(expected))).run()
    out = output_lines(capsys)
    after_menu = out[out.index("0. Exit") + 1:]   # samples start after the menu
    assert after_menu == expected


def test_bad_input_never_crashes(shop, today, capsys):
    typed = ["3", "", "3", "C001", "", "4", "nonsense", "5", "RN999",
             "7", "c002", "99", "-1", "2", "", "0"]
    Console(shop, today, make_reader(typed)).run()
    out = output_lines(capsys)
    assert out.count("Nothing entered.") == 3
    assert "ERROR [RentalNotFoundError]: No open rental with ID NONSENSE." in out
    assert out.count("Please enter a number from 0 to 8.") == 2


def test_end_of_input_exits_cleanly(capsys):
    def read(prompt):
        raise EOFError
    assert main(read=read, env={"TODAY": "2026-11-03"}, data_dir=DATA_DIR) == 0


def test_bad_today_is_reported(capsys):
    assert main(read=None, env={"TODAY": "03-11-2026"}, data_dir=DATA_DIR) == 1
    assert "TODAY must be a date like 2026-11-03" in capsys.readouterr().out
