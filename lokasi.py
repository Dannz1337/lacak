import os
import cv2
import requests
import matplotlib.pyplot as plt
from PIL import Image
import piexif
from geopy.geocoders import Nominatim
from pymediainfo import MediaInfo
import folium

OPENCAGE_API_KEY = "78b483997545434ba94266c3b223dec4"

def get_decimal_from_dms(dms, ref):
    degrees, minutes, seconds = dms
    decimal = degrees[0]/degrees[1] + minutes[0]/(minutes[1]*60) + seconds[0]/(seconds[1]*3600)
    return -decimal if ref in ['S', 'W'] else decimal

def reverse_geocode_opencage(lat, lon):
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={OPENCAGE_API_KEY}&language=id"
        response = requests.get(url)
        data = response.json()
        if data["results"]:
            return data["results"][0]["formatted"]
        return "❌ Tidak ditemukan (OpenCage)"
    except Exception as e:
        return f"❌ Error API: {e}"

def get_location_from_coordinates(lat, lon):
    alamat = reverse_geocode_opencage(lat, lon)
    if "❌" not in alamat:
        return alamat
    try:
        geolocator = Nominatim(user_agent="geoapi")
        lokasi = geolocator.reverse((lat, lon), language='id')
        return lokasi.address if lokasi else "❌ Tidak ditemukan (Nominatim)"
    except:
        return "❌ Gagal geocoding fallback"

def get_google_maps_link(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def show_map(lat, lon, alamat=""):
    map_obj = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon], popup=alamat).add_to(map_obj)
    map_obj.save("lokasi.html")

def get_device_and_time_from_image(image_path):
    try:
        img = Image.open(image_path)
        exif_data = piexif.load(img.info.get("exif", b""))
        make = exif_data["0th"].get(piexif.ImageIFD.Make, b"").decode(errors='ignore')
        model = exif_data["0th"].get(piexif.ImageIFD.Model, b"").decode(errors='ignore')
        time = exif_data["Exif"].get(piexif.ExifIFD.DateTimeOriginal, b"").decode(errors='ignore')
        return f"{make} {model}".strip(), time
    except:
        return "Tidak diketahui", ""

def check_exif_gps(image_path):
    try:
        img = Image.open(image_path)
        exif_bytes = img.info.get("exif")
        if not exif_bytes:
            return None
        exif_data = piexif.load(exif_bytes)
        gps = exif_data.get('GPS')
        if 2 not in gps or 4 not in gps:
            return None
        lat = get_decimal_from_dms(gps[2], gps[1].decode())
        lon = get_decimal_from_dms(gps[4], gps[3].decode())
        address = get_location_from_coordinates(lat, lon)
        return {"Latitude": lat, "Longitude": lon, "Alamat": address}
    except Exception:
        return None

def extract_frame_from_video(video_path, frame_number=100, output_image="temp_frame.jpg"):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    success, frame = cap.read()
    cap.release()
    if success:
        cv2.imwrite(output_image, frame)
        return output_image
    return None

def check_video_metadata(video_path):
    media_info = MediaInfo.parse(video_path)
    device = "Tidak diketahui"
    creation_time = ""
    for track in media_info.tracks:
        if track.track_type == 'General':
            device = track.encoded_application or track.tagged_application or "Tidak diketahui"
            creation_time = track.encoded_date or track.tagged_date or ""
    return device, creation_time

def proses_file(path):
    result = ""
    ext = os.path.splitext(path)[-1].lower()
    if ext in ['.jpg', '.jpeg', '.png']:
        gps = check_exif_gps(path)
        device, time = get_device_and_time_from_image(path)
        if gps:
            show_map(gps['Latitude'], gps['Longitude'], gps['Alamat'])
            result += f"Latitude: {gps['Latitude']}\nLongitude: {gps['Longitude']}\nAlamat: {gps['Alamat']}\nGoogle Maps: {get_google_maps_link(gps['Latitude'], gps['Longitude'])}\n"
        else:
            result += "❌ Metadata lokasi tidak ditemukan.\n"
        result += f"Perangkat: {device}\nWaktu: {time if time else 'Tidak diketahui'}"
    elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
        device, time = check_video_metadata(path)
        temp_img = extract_frame_from_video(path)
        if temp_img:
            gps = check_exif_gps(temp_img)
            if gps:
                show_map(gps['Latitude'], gps['Longitude'], gps['Alamat'])
                result += f"Latitude: {gps['Latitude']}\nLongitude: {gps['Longitude']}\nAlamat: {gps['Alamat']}\nGoogle Maps: {get_google_maps_link(gps['Latitude'], gps['Longitude'])}\n"
            else:
                result += "❌ Metadata lokasi dari frame tidak ditemukan.\n"
            os.remove(temp_img)
        result += f"Perangkat: {device}\nWaktu: {time if time else 'Tidak diketahui'}"
    else:
        result = "❌ Format file tidak didukung."
    return result