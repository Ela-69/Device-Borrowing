"""
/****************/  

202418930
Dương Tùng Lâm

/****************/  

"""


from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence


class DeviceStatus(Enum):
    AVAILABLE = "Available"
    BORROWED = "Borrowed"
    UNDER_MAINTENANCE = "UnderMaintenance"
    RETIRED = "Retired"


class BorrowingException(Exception):
    def __init__(self, message, inner=None):
        super().__init__(message)
        if inner is not None:
            self.__cause__ = inner


class DeviceUnavailableException(BorrowingException):
    def __init__(self, device_id, current_status):
        super().__init__(f"Thiết bị {device_id} không sẵn sàng ({current_status.value})")
        self.device_id = device_id
        self.current_status = current_status


class DeviceInUseException(BorrowingException):
    def __init__(self, device_id):
        super().__init__(f"Thiết bị {device_id} đang được mượn, chưa thể thay đổi")
        self.device_id = device_id


class BorrowLimitExceededException(BorrowingException):
    def __init__(self, borrower_id, maximum_devices):
        super().__init__(f"Người mượn {borrower_id} đã đạt tối đa {maximum_devices} thiết bị")
        self.borrower_id = borrower_id
        self.maximum_devices = maximum_devices


class InvalidBorrowPeriodException(BorrowingException):
    def __init__(self, device_id, requested_days, max_days):
        super().__init__(
            f"Thiết bị {device_id}: yêu cầu {requested_days} ngày, tối đa {max_days} ngày"
        )
        self.device_id = device_id
        self.requested_days = requested_days
        self.max_days = max_days


class InvalidPeriodRangeException(BorrowingException):
    def __init__(self, device_id, from_period, to_period, max_periods):
        super().__init__(
            f"Thiết bị {device_id}: tiết {from_period}-{to_period} nằm ngoài phạm vi 1-{max_periods}"
        )
        self.device_id = device_id
        self.max_periods = max_periods


class DuplicateDeviceException(BorrowingException):
    def __init__(self, device_id):
        super().__init__(f"Thiết bị {device_id} đã có trong phiếu")
        self.device_id = device_id


class DeviceNotInSlipException(BorrowingException):
    def __init__(self, device_id):
        super().__init__(f"Thiết bị {device_id} không thuộc phiếu")
        self.device_id = device_id


class DeviceAlreadyReturnedException(BorrowingException):
    def __init__(self, device_id):
        super().__init__(f"Thiết bị {device_id} đã được trả trước đó")
        self.device_id = device_id


class InvalidReturnDateException(BorrowingException):
    def __init__(self, device_id, borrowed_date, returned_date):
        super().__init__(
            f"Ngày trả {returned_date:%d/%m/%Y} trước ngày mượn {borrowed_date:%d/%m/%Y} ({device_id})"
        )
        self.device_id = device_id


def require_text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} không được rỗng")
    return value.strip()


def require_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} phải là số nguyên")
    return value


class Device(ABC):
    MIN_YEAR = 1950

    def __init__(self, device_id: str, name: str, year_in_use: int, price: Decimal,
                 status: DeviceStatus = DeviceStatus.AVAILABLE):
        if isinstance(price, bool) or not isinstance(price, (int, Decimal)):
            raise ValueError("Giá mua phải là số")
        price = Decimal(price)
        if not price.is_finite() or price <= 0:
            raise ValueError("Giá mua phải lớn hơn 0")
        require_int(year_in_use, "Năm đưa vào sử dụng")
        if not Device.MIN_YEAR <= year_in_use <= datetime.now().year:
            raise ValueError(f"Năm đưa vào sử dụng phải trong khoảng {Device.MIN_YEAR}-{datetime.now().year}")
        if not isinstance(status, DeviceStatus) or status == DeviceStatus.BORROWED:
            raise ValueError("Trạng thái khởi tạo không hợp lệ")
        self._device_id = require_text(device_id, "Mã thiết bị")
        self.name = require_text(name, "Tên thiết bị")
        self.year_in_use = year_in_use
        self.price = price
        self._status = status

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def status(self) -> DeviceStatus:
        return self._status

    def change_status(self, new_status: DeviceStatus):
        if self._status == DeviceStatus.BORROWED:
            raise DeviceInUseException(self.device_id)
        if not isinstance(new_status, DeviceStatus) or new_status == DeviceStatus.BORROWED:
            raise ValueError("Trạng thái Borrowed chỉ được đặt thông qua phiếu mượn")
        self._status = new_status

    @abstractmethod
    def annual_maintenance_cost(self) -> Decimal:
        ...

    def age(self) -> int:
        return datetime.now().year - self.year_in_use

    def __str__(self):
        return f"[{self.device_id}] {self.name} | {self.year_in_use} | {self.price:,} | {self.status.value}"


class TeachingDevice(Device):
    def __init__(self, device_id, name, year_in_use, price, max_days: int, max_periods: int,
                 status=DeviceStatus.AVAILABLE):
        super().__init__(device_id, name, year_in_use, price, status)
        self.max_days = require_int(max_days, "Số ngày tối đa")
        self.max_periods = require_int(max_periods, "Số tiết tối đa")

    def mark_as_borrowed(self):
        if self._status != DeviceStatus.AVAILABLE:
            raise DeviceUnavailableException(self.device_id, self._status)
        self._status = DeviceStatus.BORROWED

    def mark_as_available(self):
        self._status = DeviceStatus.AVAILABLE


class AirConditionerRemote(TeachingDevice):
    def __init__(self, device_id, name, year_in_use, price, status=DeviceStatus.AVAILABLE):
        super().__init__(device_id, name, year_in_use, price, 2, 4, status)

    def annual_maintenance_cost(self) -> Decimal:
        return self.price * Decimal("0.05")


class Microphone(TeachingDevice):
    def __init__(self, device_id, name, year_in_use, price, status=DeviceStatus.AVAILABLE):
        super().__init__(device_id, name, year_in_use, price, 1, 3, status)

    def annual_maintenance_cost(self) -> Decimal:
        return self.price * Decimal("0.1")


class ProjectorRemote(TeachingDevice):
    def __init__(self, device_id, name, year_in_use, price, status=DeviceStatus.AVAILABLE):
        super().__init__(device_id, name, year_in_use, price, 3, 6, status)

    def annual_maintenance_cost(self) -> Decimal:
        return self.price * Decimal("0.03")


class ClassRoom:
    def __init__(self, room_id: str, name: str, capacity: int):
        if require_int(capacity, "Sức chứa") <= 0:
            raise ValueError("Sức chứa phải lớn hơn 0")
        self.room_id = require_text(room_id, "Mã phòng")
        self.name = require_text(name, "Tên phòng")
        self.capacity = capacity
        self._devices: list[Device] = []

    @property
    def devices(self) -> Sequence[Device]:
        return tuple(self._devices)

    def add_device(self, device: Device):
        if device is None:
            raise ValueError("Thiết bị không được null")
        if self.find_device(device.device_id) is not None:
            raise ValueError(f"Thiết bị {device.device_id} đã có trong phòng")
        self._devices.append(device)

    def remove_device(self, device_id: str) -> bool:
        d = self.find_device(device_id)
        if d is None:
            return False
        if d.status == DeviceStatus.BORROWED:
            raise DeviceInUseException(device_id)
        self._devices.remove(d)
        return True

    def find_device(self, device_id: str) -> Optional[Device]:
        return next((d for d in self._devices if d.device_id == device_id), None)

    def calculate_annual_maintenance_cost(self) -> Decimal:
        return sum((d.annual_maintenance_cost() for d in self._devices), Decimal(0))

    def get_devices_requiring_maintenance(self) -> list[Device]:
        return [d for d in self._devices
                if d.status == DeviceStatus.UNDER_MAINTENANCE or d.age() > 5]


class IBorrower(ABC):
    @property
    @abstractmethod
    def borrower_id(self) -> str: ...

    @property
    @abstractmethod
    def full_name(self) -> str: ...

    @abstractmethod
    def get_maximum_devices(self) -> int: ...


class Lecturer(IBorrower):
    def __init__(self, borrower_id, full_name):
        self._id = require_text(borrower_id, "Mã người mượn")
        self._name = require_text(full_name, "Họ tên")

    borrower_id = property(lambda self: self._id)
    full_name = property(lambda self: self._name)

    def get_maximum_devices(self) -> int:
        return 3


class TeachingAssistant(IBorrower):
    def __init__(self, borrower_id, full_name):
        self._id = require_text(borrower_id, "Mã người mượn")
        self._name = require_text(full_name, "Họ tên")

    borrower_id = property(lambda self: self._id)
    full_name = property(lambda self: self._name)

    def get_maximum_devices(self) -> int:
        return 2


class BorrowItem:
    def __init__(self, device: TeachingDevice, borrowed_date: datetime, due_date: datetime,
                 from_period: int, to_period: int):
        if device is None:
            raise ValueError("Device không được null")
        if due_date < borrowed_date:
            raise ValueError("Hạn trả phải sau hoặc bằng ngày mượn")
        self._device = device
        self._borrowed_date = borrowed_date
        self._due_date = due_date
        self._returned_date: Optional[datetime] = None
        self.set_periods(from_period, to_period)

    device = property(lambda self: self._device)
    borrowed_date = property(lambda self: self._borrowed_date)
    due_date = property(lambda self: self._due_date)
    returned_date = property(lambda self: self._returned_date)
    from_period = property(lambda self: self._from_period)
    to_period = property(lambda self: self._to_period)

    @from_period.setter
    def from_period(self, value):
        self.set_periods(value, self._to_period)

    @to_period.setter
    def to_period(self, value):
        self.set_periods(self._from_period, value)

    def set_periods(self, from_period: int, to_period: int):
        require_int(from_period, "Tiết bắt đầu")
        require_int(to_period, "Tiết kết thúc")
        if from_period < 1 or to_period < from_period or to_period > self._device.max_periods:
            raise InvalidPeriodRangeException(self._device.device_id, from_period, to_period,
                                              self._device.max_periods)
        self._from_period, self._to_period = from_period, to_period

    @property
    def is_returned(self) -> bool:
        return self._returned_date is not None

    def return_item(self, returned_date: datetime):
        if self.is_returned:
            raise DeviceAlreadyReturnedException(self._device.device_id)
        if not isinstance(returned_date, datetime):
            raise ValueError("Ngày trả không hợp lệ")
        if returned_date < self._borrowed_date:
            raise InvalidReturnDateException(self._device.device_id, self._borrowed_date, returned_date)
        self._returned_date = returned_date

    def late_days(self) -> int:
        if not self.is_returned:
            return 0
        return max(0, (self._returned_date - self._due_date).days)


class BorrowingSlip:
    LATE_FEE_PER_DAY = Decimal(10000)

    def __init__(self, slip_id: str, borrower: IBorrower, teaching_room: str,
                 borrowed_date: Optional[datetime] = None):
        if borrower is None:
            raise ValueError("Người mượn không được null")
        self._slip_id = require_text(slip_id, "Mã phiếu")
        self._borrower = borrower
        self._teaching_room = require_text(teaching_room, "Phòng dạy")
        self._borrowed_date = borrowed_date or datetime.now()
        self._items: list[BorrowItem] = []

    slip_id = property(lambda self: self._slip_id)
    borrower = property(lambda self: self._borrower)
    teaching_room = property(lambda self: self._teaching_room)
    borrowed_date = property(lambda self: self._borrowed_date)

    @property
    def items(self) -> Sequence[BorrowItem]:
        return tuple(self._items)

    def _validate_borrowing(self, device, borrow_days):
        if device is None:
            raise ValueError("Thiết bị không được null")
        if isinstance(borrow_days, bool) or not isinstance(borrow_days, int):
            raise ValueError("Số ngày mượn phải là số nguyên")
        if borrow_days <= 0 or borrow_days > device.max_days:
            raise InvalidBorrowPeriodException(device.device_id, borrow_days, device.max_days)
        if any(i.device.device_id == device.device_id for i in self._items):
            raise DuplicateDeviceException(device.device_id)
        if len(self._items) >= self._borrower.get_maximum_devices():
            raise BorrowLimitExceededException(self._borrower.borrower_id,
                                               self._borrower.get_maximum_devices())
        if device.status != DeviceStatus.AVAILABLE:
            raise DeviceUnavailableException(device.device_id, device.status)

    def add_device(self, device: TeachingDevice, borrow_days: int,
                   from_period: int = 1, to_period: int = 1):
        self._validate_borrowing(device, borrow_days)
        item = BorrowItem(device, self._borrowed_date,
                          self._borrowed_date + timedelta(days=borrow_days),
                          from_period, to_period)
        device.mark_as_borrowed()
        self._items.append(item)

    def return_device(self, device_id: str, returned_date: datetime) -> Decimal:
        device_id = require_text(device_id, "Mã thiết bị")
        item = next((i for i in self._items if i.device.device_id == device_id), None)
        if item is None:
            raise DeviceNotInSlipException(device_id)
        item.return_item(returned_date)
        item.device.mark_as_available()
        return self.LATE_FEE_PER_DAY * item.late_days()

    def calculate_total_late_fee(self) -> Decimal:
        return sum((self.LATE_FEE_PER_DAY * i.late_days() for i in self._items), Decimal(0))


DEVICE_TYPES = {
    "1": ("Điều khiển điều hòa", AirConditionerRemote),
    "2": ("Micro", Microphone),
    "3": ("Điều khiển máy chiếu", ProjectorRemote),
}
STATUSES = {
    "1": DeviceStatus.AVAILABLE,
    "2": DeviceStatus.UNDER_MAINTENANCE,
    "3": DeviceStatus.RETIRED,
}
BORROWER_TYPES = {"1": Lecturer, "2": TeachingAssistant}


def today() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def read_text(prompt: str) -> str:
    return input(prompt).strip()


def read_int(prompt: str) -> int:
    return int(input(prompt))


def read_date(prompt: str) -> datetime:
    s = input(f"{prompt} (dd/mm/yyyy, Enter = hôm nay): ").strip()
    return today() if not s else datetime.strptime(s, "%d/%m/%Y")


def read_choice(prompt: str, options: dict) -> str:
    key = input(prompt).strip()
    if key not in options:
        raise ValueError("Lựa chọn không hợp lệ")
    return key


class App:
    def __init__(self):
        self.room = ClassRoom("P101", "Phòng 101", 60)
        self.borrowers: dict[str, IBorrower] = {}
        self.slips: dict[str, BorrowingSlip] = {}

    def get_slip(self) -> BorrowingSlip:
        slip = self.slips.get(read_text("Mã phiếu: "))
        if slip is None:
            raise ValueError("Không tìm thấy phiếu")
        return slip

    def get_device(self) -> Device:
        device = self.room.find_device(read_text("Mã thiết bị: "))
        if device is None:
            raise ValueError("Không tìm thấy thiết bị")
        return device

    def add_device(self):
        for k, (label, _) in DEVICE_TYPES.items():
            print(f"  {k}. {label}")
        cls = DEVICE_TYPES[read_choice("Loại thiết bị: ", DEVICE_TYPES)][1]
        device = cls(read_text("Mã: "), read_text("Tên: "),
                     read_int("Năm đưa vào sử dụng: "), Decimal(read_text("Giá mua: ")))
        self.room.add_device(device)
        print("Đã thêm:", device)

    def set_device_status(self):
        device = self.get_device()
        print("  1. Available  2. UnderMaintenance  3. Retired")
        device.change_status(STATUSES[read_choice("Trạng thái mới: ", STATUSES)])
        print("Đã cập nhật:", device)

    def remove_device(self):
        if self.room.remove_device(read_text("Mã thiết bị: ")):
            print("Đã xóa thiết bị khỏi phòng")
        else:
            print("Không tìm thấy thiết bị")

    def add_borrower(self):
        print("  1. Giảng viên  2. Trợ giảng")
        cls = BORROWER_TYPES[read_choice("Loại người mượn: ", BORROWER_TYPES)]
        b = cls(read_text("Mã người mượn: "), read_text("Họ tên: "))
        if b.borrower_id in self.borrowers:
            raise ValueError("Mã người mượn đã tồn tại")
        self.borrowers[b.borrower_id] = b
        print(f"Đã thêm {type(b).__name__}: {b.full_name} (tối đa {b.get_maximum_devices()} thiết bị)")

    def create_slip(self):
        slip_id = read_text("Mã phiếu: ")
        if slip_id in self.slips:
            raise ValueError("Mã phiếu đã tồn tại")
        borrower = self.borrowers.get(read_text("Mã người mượn: "))
        if borrower is None:
            raise ValueError("Không tìm thấy người mượn")
        slip = BorrowingSlip(slip_id, borrower, read_text("Phòng dạy: "), read_date("Ngày mượn"))
        self.slips[slip.slip_id] = slip
        print("Đã tạo phiếu", slip.slip_id)

    def add_to_slip(self):
        slip = self.get_slip()
        device = self.get_device()
        days = read_int("Số ngày mượn: ")
        from_p = read_int("Từ tiết: ")
        to_p = read_int("Đến tiết: ")
        slip.add_device(device, days, from_p, to_p)
        print("Đã thêm vào phiếu:", device)

    def return_device(self):
        slip = self.get_slip()
        fee = slip.return_device(read_text("Mã thiết bị: "), read_date("Ngày trả"))
        print(f"Đã trả. Phí muộn: {fee:,}")

    def show_slip(self):
        slip = self.get_slip()
        print(f"Phiếu {slip.slip_id} | {slip.borrower.full_name} | {slip.teaching_room} | "
              f"{slip.borrowed_date:%d/%m/%Y}")
        for i in slip.items:
            state = f"đã trả {i.returned_date:%d/%m/%Y}" if i.is_returned else "chưa trả"
            print(f"  {i.device.device_id} | hạn {i.due_date:%d/%m/%Y} | tiết {i.from_period}-{i.to_period} "
                  f"| {state} | muộn {i.late_days()} ngày")
        print(f"Tổng phí muộn: {slip.calculate_total_late_fee():,}")

    def show_report(self):
        if not self.slips:
            print("Chưa có phiếu nào")
        for slip in self.slips.values():
            late = [i for i in slip.items if i.late_days() > 0]
            pending = [i for i in slip.items if not i.is_returned]
            if not late and not pending:
                continue
            print(f"Phiếu {slip.slip_id} ({slip.borrower.full_name})")
            for i in late:
                print(f"  Trả muộn: {i.device.device_id} - {i.late_days()} ngày")
            for i in pending:
                print(f"  Chưa trả: {i.device.device_id} - hạn {i.due_date:%d/%m/%Y}")

    def show_devices(self):
        for d in self.room.devices:
            print(" ", d)
        print(f"Chi phí bảo trì dự kiến/năm: {self.room.calculate_annual_maintenance_cost():,.0f}")
        print("Cần bảo trì:", [d.device_id for d in self.room.get_devices_requiring_maintenance()])

    def run(self):
        actions = {
            "1": ("Thêm thiết bị", self.add_device),
            "2": ("Đổi trạng thái thiết bị", self.set_device_status),
            "3": ("Thêm người mượn", self.add_borrower),
            "4": ("Tạo phiếu mượn", self.create_slip),
            "5": ("Thêm thiết bị vào phiếu", self.add_to_slip),
            "6": ("Trả thiết bị", self.return_device),
            "7": ("Xem phiếu", self.show_slip),
            "8": ("Xem thiết bị / chi phí bảo trì", self.show_devices),
            "9": ("Báo cáo phiếu trả muộn / chưa trả", self.show_report),
            "10": ("Xóa thiết bị khỏi phòng", self.remove_device),
            "0": ("Thoát", None),
        }
        while True:
            print("\n==== MENU ====")
            for k, (label, _) in actions.items():
                print(f"{k}. {label}")
            choice = input("Chọn: ").strip()
            if choice == "0":
                break
            if choice not in actions:
                print("Lựa chọn không hợp lệ")
                continue
            try:
                actions[choice][1]()
            except BorrowingException as ex:
                print(f"[Lỗi nghiệp vụ - {type(ex).__name__}] {ex}")
            except (ValueError, ArithmeticError) as ex:
                print(f"[Dữ liệu không hợp lệ] {ex}")
            finally:
                print("-" * 30)


if __name__ == "__main__":
    App().run()
