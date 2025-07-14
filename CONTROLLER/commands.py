# commands.py
BLE_CHAR_STRING = "0000{}-0000-1000-8000-00805f9b34fb"
GOPRO_BASE_UUID = "B5F9{}-aa8d-11e3-9046-0002a5d5c51b"

class Commands:
	class Shutter:
		Start = bytearray(b'\x03\x01\x01\x01')
		Stop = bytearray(b'\x03\x01\x01\x00')
	class Mode:
		Video = bytearray(b'\x03\x02\x01\x00')
		Photo = bytearray(b'\x03\x02\x01\x01')
		Multishot = bytearray(b'\x03\x02\x01\x02')
	class Submode:
		class Video:
			Single =    bytearray(b'\x05\x03\x01\x00\x01\x00')
			TimeLapse = bytearray(b'\x05\x03\x01\x00\x01\x01')
		class Photo:
			Single = bytearray(b'\x05\x03\x01\x01\x01\x01')
			Night = bytearray(b'\x05\x03\x01\x01\x01\x02')
		class Multishot:
			Burst =      bytearray(b'\x05\x03\x01\x02\x01\x00')
			TimeLapse =  bytearray(b'\x05\x03\x01\x02\x01\x01')
			NightLapse = bytearray(b'\x05\x03\x01\x02\x01\x02')

	class Basic:
		Sleep = bytearray(b'\x01\x05')
		PowerOffForce = bytearray(b'\x01\x04')
		HiLightTag = bytearray(b'\x01\x18')
	class Locate:
		ON = bytearray(b'\x03\x16\x01\x01')
		OFF = bytearray(b'\x03\x16\x01\x00')
	class WiFi:
		ON = bytearray(b'\x03\x17\x01\x01')
		OFF = bytearray(b'\x03\x17\x01\x00')

	# OpenGoPro commands
	class Preset:
		Activity = bytearray(b'\x06\x40\x04\x00\x00\x00\x01')
		BurstPhoto = bytearray(b'\x06\x40\x04\x00\x01\x00\x02')
		Cinematic = bytearray(b'\x06\x40\x04\x00\x00\x00\x02')
		LiveBurst = bytearray(b'\x06\x40\x04\x00\x01\x00\x01')
		NightPhoto = bytearray(b'\x06\x40\x04\x00\x01\x00\x03')
		NightLapse = bytearray(b'\x06\x40\x04\x00\x02\x00\x02')
		Photo = bytearray(b'\x06\x40\x04\x00\x01\x00\x00')
		SloMo = bytearray(b'\x06\x40\x04\x00\x00\x00\x03')
		Standard = bytearray(b'\x06\x40\x04\x00\x00\x00\x00')
		TimeLapse = bytearray(b'\x06\x40\x04\x00\x02\x00\x01')
		TimeWarp = bytearray(b'\x06\x40\x04\x00\x02\x00\x00')
		MaxPhoto = bytearray(b'\x06\x40\x04\x00\x04\x00\x00')
		MaxTimewarp = bytearray(b'\x06\x40\x04\x00\x05\x00\x00')
		MaxVideo = bytearray(b'\x06\x40\x04\x00\x03\x00\x00')
	class PresetGroup:
		Video = bytearray(b'\x04\x3E\x02\x03\xE8')
		Photo = bytearray(b'\x04\x3E\x02\x03\xE9')
		Timelapse = bytearray(b'\x04\x3E\x02\x03\xEA')
	class Turbo:
		ON = bytearray(b'\x04\xF1\x6B\x08\x01')
		OFF = bytearray(b'\x04\xF1\x6B\x08\x00')
	class Analytics:
		SetThirdPartyClient = bytearray(b'\x01\x50')

class Settings:
    class Resolution:
        RES_1080p = bytearray(b'\x04\x02\x01\x09')
        RES_2_7K = bytearray(b'\x04\x02\x01\x04')
        RES_4K = bytearray(b'\x04\x02\x01\x01')
        RES_5_3K = bytearray(b'\x04\x02\x01\x64')
    class Framerate:
        FPS_30 = bytearray(b'\x04\x03\x01\x08')
        FPS_60 = bytearray(b'\x04\x03\x01\x05')
        FPS_120 = bytearray(b'\x04\x03\x01\x01')
        FPS_240 = bytearray(b'\x04\x03\x01\x00')
    class VideoLens:
        Wide = bytearray(b'\x04\x79\x01\x00')
        Narrow = bytearray(b'\x04\x79\x01\x02')
        Superview = bytearray(b'\x04\x79\x01\x03')
        Linear = bytearray(b'\x04\x79\x01\x04')
        MaxSuperview = bytearray(b'\x04\x79\x01\x07')
        LinearLevel = bytearray(b'\x04\x79\x01\x08')
    class AutoPowerDown:
        Never = bytearray(b'\x04\x3b\x01\x00')
        Minutes_5 = bytearray(b'\x04\x3b\x01\x04') 
        Minutes_15 = bytearray(b'\x04\x3b\x01\x06')
        Minutes_30 = bytearray(b'\x04\x3b\x01\x07') 

class GoProUuid:
	Control = BLE_CHAR_STRING.format("FEA6".lower())
	Info = BLE_CHAR_STRING.format("180A".lower())
	Battery = BLE_CHAR_STRING.format("180F".lower())
	
	FirmwareVersion = BLE_CHAR_STRING.format("2A26".lower())
	SerialNumber = BLE_CHAR_STRING.format("2A25".lower())
	BatteryLevel = BLE_CHAR_STRING.format("2A19".lower())

	COMMAND_REQ_UUID = GOPRO_BASE_UUID.format("0072")
	COMMAND_RSP_UUID = GOPRO_BASE_UUID.format("0073")
	SETTINGS_REQ_UUID = GOPRO_BASE_UUID.format("0074")
	SETTINGS_RSP_UUID = GOPRO_BASE_UUID.format("0075")
	QUERY_REQ_UUID = GOPRO_BASE_UUID.format("0076")
	QUERY_RSP_UUID = GOPRO_BASE_UUID.format("0077")
	WIFI_AP_SSID_UUID = GOPRO_BASE_UUID.format("0002")
	WIFI_AP_PASSWORD_UUID = GOPRO_BASE_UUID.format("0003")
	NETWORK_MANAGEMENT_REQ_UUID = GOPRO_BASE_UUID.format("0091")
	NETWORK_MANAGEMENT_RSP_UUID = GOPRO_BASE_UUID.format("0092")
