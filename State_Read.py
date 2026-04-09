import serial
import time
import msvcrt

PORT = "COM3"
BAUDRATE = 9600
TIMEOUT = 1

# Sürekli kilo okuma sorgusu
READ_REQUEST = bytes.fromhex("01 03 9C 40 00 06 EA 4C")

# Komutlar
TARE_REQUEST  = bytes.fromhex("01 06 9C A5 00 14 B7 B6")
RESET_REQUEST = bytes.fromhex("01 06 9C A5 00 28 B7 A7")
ZERO_REQUEST  = bytes.fromhex("01 06 9C A5 00 1E 37 B1")
SAVE_REQUEST  = bytes.fromhex("01 06 9C A5 00 0A 37 BE")


def create_serial():
    return serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_TWO,
        timeout=TIMEOUT
    )


def parse_modbus_response(data, start_register=40000):
    if len(data) < 5:
        print("Geçersiz veri: çok kısa")
        return None

    slave_id = data[0]
    function_code = data[1]

    if function_code & 0x80:
        exception_code = data[2] if len(data) > 2 else None
        print(f"RECV: {data.hex(' ').upper()}")
        print(f"HATA: Modbus exception response. Code: {exception_code}")
        print("-" * 50)
        return None

    byte_count = data[2]
    register_data = data[3:3 + byte_count]
    crc = data[3 + byte_count: 3 + byte_count + 2]

    if len(register_data) != byte_count:
        print("Byte count ile veri uzunluğu uyuşmuyor")
        return None

    if byte_count % 2 != 0:
        print("Register verisi çift byte olmalı")
        return None

    registers = []
    for i in range(0, len(register_data), 2):
        value = (register_data[i] << 8) | register_data[i + 1]
        registers.append(value)

    print(f"RECV: {data.hex(' ').upper()}")
    print(f"DONE: Read Holding Registers (code ${function_code:02X})")
    print("PASS: Normal response")
    print(f"{len(registers)} holding registers were processed.")

    for i, value in enumerate(registers):
        print(f"Value of holding register {start_register + i} is {value}")

    print("-" * 50)
    return registers


def parse_write_response(data, action_name="Komut"):
    """
    Modbus 06 cevabı:
    Slave ID | Function | Addr Hi | Addr Lo | Data Hi | Data Lo | CRC Lo | CRC Hi
    """
    if len(data) < 8:
        print(f"{action_name} cevabı geçersiz: çok kısa")
        print(f"RECV: {data.hex(' ').upper()}")
        print("-" * 50)
        return False

    slave_id = data[0]
    function_code = data[1]

    if function_code & 0x80:
        exception_code = data[2] if len(data) > 2 else None
        print(f"RECV: {data.hex(' ').upper()}")
        print(f"{action_name} başarısız. Modbus exception code: {exception_code}")
        print("-" * 50)
        return False

    if function_code == 0x06:
        addr = (data[2] << 8) | data[3]
        value = (data[4] << 8) | data[5]

        print(f"RECV: {data.hex(' ').upper()}")
        print("DONE: Write Single Register (code $06)")
        print(f"PASS: {action_name} komutu kabul edildi")
        print(f"Slave ID : {slave_id}")
        print(f"Register : {addr} (0x{addr:04X})")
        print(f"Value    : {value} (0x{value:04X})")
        print("-" * 50)
        return True

    print(f"RECV: {data.hex(' ').upper()}")
    print(f"Beklenmeyen function code: {function_code:02X}")
    print("-" * 50)
    return False


def read_weight_once(ser):
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    ser.write(READ_REQUEST)
    time.sleep(0.1)

    response = ser.read(17)

    if not response:
        print("Cihazdan cevap gelmedi")
        print("-" * 50)
        return None

    return parse_modbus_response(response, start_register=40000)


def send_command_once(ser, request, action_name, key_name):
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    print(f"\n[{key_name} tuşu algılandı] {action_name} komutu gönderiliyor...")
    print(f"SEND: {request.hex(' ').upper()}")

    ser.write(request)
    time.sleep(0.2)

    response = ser.read(8)

    if not response:
        print(f"{action_name} komutuna cevap gelmedi")
        print("-" * 50)
        return False

    return parse_write_response(response, action_name=action_name)


if __name__ == "__main__":
    ser = create_serial()

    try:
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()

                if key in (b'd', b'D'):
                    ok = send_command_once(ser, TARE_REQUEST, "Dara", "D")
                    if ok:
                        print("Dara işlemi başarılı. Kilo okuma moduna geri dönülüyor.\n")
                    else:
                        print("Dara işlemi başarısız. Kilo okuma moduna geri dönülüyor.\n")

                elif key in (b'r', b'R'):
                    ok = send_command_once(ser, RESET_REQUEST, "Reset", "R")
                    if ok:
                        print("Reset işlemi başarılı. Kilo okuma moduna geri dönülüyor.\n")
                    else:
                        print("Reset işlemi başarısız. Kilo okuma moduna geri dönülüyor.\n")

                elif key in (b'z', b'Z'):
                    ok = send_command_once(ser, ZERO_REQUEST, "Sıfırlama", "Z")
                    if ok:
                        print("Sıfırlama işlemi başarılı. Kilo okuma moduna geri dönülüyor.\n")
                    else:
                        print("Sıfırlama işlemi başarısız. Kilo okuma moduna geri dönülüyor.\n")

                elif key in (b's', b'S'):
                    ok = send_command_once(ser, SAVE_REQUEST, "Kaydet", "S")
                    if ok:
                        print("Kaydet işlemi başarılı. Kilo okuma moduna geri dönülüyor.\n")
                    else:
                        print("Kaydet işlemi başarısız. Kilo okuma moduna geri dönülüyor.\n")

            read_weight_once(ser)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Program durduruldu.")
    finally:
        ser.close()