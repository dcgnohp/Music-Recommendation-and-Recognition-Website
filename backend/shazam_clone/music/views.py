from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User, auth
from django.contrib.auth.decorators import login_required
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import json
from django.http import HttpResponse
from pprint import pprint
import random
from django import template
from django.template.defaultfilters import register
from django.http import JsonResponse
import subprocess
from spotipy import Spotify


# Create your views here.
@login_required(login_url='login')
def index(request):
    top_artists_info = get_top_artists()
    top_tracks_info = get_top_tracks()
    first_six_tracks = top_tracks_info[:6]
    second_six_tracks = top_tracks_info[6:12]
    third_six_tracks = top_tracks_info[12:18]
    
    audio_details = get_audio_detail()
    
    # Tạo một dictionary để map id với thông tin audio
    audio_dict = {detail['id']: detail for detail in audio_details}
    
    # Thêm thông tin audio vào mỗi track
    for track_list in [first_six_tracks, second_six_tracks, third_six_tracks]:
        for track in track_list:
            audio_info = audio_dict.get(track['id'])
            if audio_info:
                track['audio_url'] = audio_info['url']
                track['duration_ms'] = audio_info['duration_ms']

    context = {
        'top_artists_info': top_artists_info,
        'first_six_tracks': first_six_tracks,
        'second_six_tracks': second_six_tracks,
        'third_six_tracks': third_six_tracks,
        'audio_details': audio_details
    }
    
    return render(request, 'index.html', context)

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            messages.success(request, 'Login successful')
            return redirect('/')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('login')
    return render(request, 'login.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']        
        if password == password2:
           if User.objects.filter(email=email).exists():
               messages.error(request, 'Email already exists')
               return redirect('signup')
           elif User.objects.filter(username=username).exists():
               messages.error(request, 'Username already exists')
               return redirect('signup')
           else:
               user = User.objects.create_user(username=username, email=email, password=password)
               user.save()
               user_login=auth.authenticate(username=username, password=password)
               auth.login(request, user_login)
               return redirect('index')
        else:
            messages.error(request, 'Passwords do not match')
            return redirect('signup')
    else:
        return render(request, 'signup.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    request.session.flush()  # Xóa toàn bộ session
    messages.success(request, 'You have been logged out.')
    return redirect('login')

def music(request, pk):   
    scope = 'user-top-read'  # Define the scope
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id="8ea6321dd0e14815a75db4af02ba3a7b",
        client_secret="62ac40dff1a947de92df5df18b55312b",
        redirect_uri="http://localhost:8000/callback",
        scope=scope
    ))
    track = sp.track(pk)  # Use pk as the track URN

    # Lấy thông tin audio từ audio_details.json
    with open('audio_details.json', 'r', encoding='utf-8') as f:
        audio_details = json.load(f)

    # Tìm thông tin audio bất kỳ từ danh sách còn lại
    audio_info = next((item for item in audio_details if item['audio_detail_query'].lower() == track['name'].lower()), None)

    track_info = {
        'id': track['id'],
        'name': track['name'],
        'artist': track['artists'][0]['name'] if track['artists'] else None,
        'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
        'duration_ms': audio_info['duration_ms'] if audio_info else '3:30',
        'audio_url': audio_info['url'] if audio_info else None
    }
    print(f"Audio URL: {track_info['audio_url']}")
    return render(request, 'music.html', {'track_info': track_info})

def get_top_artists():   
    scope = 'user-top-read'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="8ea6321dd0e14815a75db4af02ba3a7b",
    client_secret="62ac40dff1a947de92df5df18b55312b",
    redirect_uri="http://localhost:8000/callback",
    scope=scope
    ))
    ranges = ['short_term', 'medium_term', 'long_term']    
    top_artists_info = []  # List to store artist information

    for sp_range in ranges:
        results = sp.current_user_top_artists(time_range=sp_range, limit=50)

        for item in results['items']:
            artist_id = item['id']  # Get artist ID
            artist_name = item['name']  # Get artist name
            artist_image = item['images'][0]['url'] if item['images'] else None  # Get artist image URL

            # Append artist info to the list
            top_artists_info.append({
                'id': artist_id,
                'name': artist_name,
                'image': artist_image
            })

    return top_artists_info

def get_top_tracks():
    scope = 'user-top-read'
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="8ea6321dd0e14815a75db4af02ba3a7b",
    client_secret="62ac40dff1a947de92df5df18b55312b",
    redirect_uri="http://localhost:8000/callback",
    scope=scope
    ))
    ranges = ['short_term', 'medium_term', 'long_term']    
    top_tracks_info = []  # List to store artist information

    for sp_range in ranges:
        results = sp.current_user_top_tracks(time_range=sp_range, limit=18)

        for item in results['items']:
            track_id = item['id']  # Get track ID
            track_name = item['name']  # Get track name
            track_artist = item['artists'][0]['name'] if item['artists'] else None  # Get track artist name
            track_image = item['album']['images'][0]['url'] if item['album']['images'] else None  # Get track image URL

            # Append track info to the list
            top_tracks_info.append({
                'id': track_id,
                'name': track_name,
                'image': track_image,
                'artist': track_artist
            })

    return top_tracks_info

def get_audio_detail():
    with open('audio_details.json', 'r', encoding='utf-8') as f:
        audio_details = json.load(f)
    return audio_details  # Giả sử audio_details chứa danh sách các dict với 'url' và 'duration'

def profile(request, pk):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id="8ea6321dd0e14815a75db4af02ba3a7b",
        client_secret="62ac40dff1a947de92df5df18b55312b"
    ))

    artist = sp.artist(pk)
    top_tracks = sp.artist_top_tracks(pk)
    albums = sp.artist_albums(pk, album_type='album')

    # Ước tính số lượng người nghe hàng tháng
    followers = artist['followers']['total']
    popularity = artist['popularity']
    estimated_monthly_listeners = estimate_monthly_listeners(followers, popularity)

    # Lấy URL hình ảnh đầu tiên nếu có
    artist_image_url = artist['images'][0]['url'] if artist['images'] else ''

    context = {
        'artist': artist,
        'top_tracks': top_tracks['tracks'][:10],
        'albums': albums['items'][:10],
        'estimated_monthly_listeners': estimated_monthly_listeners,
        'artist_image_url': artist_image_url  # Thêm URL hình ảnh vào context
    }

    return render(request, 'profile.html', context)

def estimate_monthly_listeners(followers, popularity):
    # Đây chỉ là một ước tính đơn giản, không chính xác
    base = followers * (popularity / 100)
    variation = random.uniform(0.8, 1.2)  # Thêm một chút biến động
    return int(base * variation)

def search(request):
    if request.method == 'GET':
        query = request.GET.get('q', '')
        if query:
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id="8ea6321dd0e14815a75db4af02ba3a7b",
                client_secret="62ac40dff1a947de92df5df18b55312b"
            ))
            results = sp.search(q=query, type='artist', limit=10)
            results1 = sp.search(q=query, type='track', limit=15)
            
            # Process the results
            artists = results['artists']['items'] if 'artists' in results else []
            tracks = results1['tracks']['items'] if 'tracks' in results1 else []
            
            context = {
                'query': query,
                'artists': artists,
                'tracks': tracks
            }
            return render(request, 'search.html', context)
    return render(request, 'search.html')

def shazam_view(request):
    context = {
        'latest_recognized_song': latest_recognized_song
    }
    return render(request, 'shazam.html', context)


def artist_page(request):
    all_artists = get_top_artists()  # Đảm bảo hàm này trả về dữ liệu
    context = {
        'all_artists': all_artists,
    }
    return render(request, 'artist_page.html', context)


# Biến toàn cục hoặc lưu vào database/file tùy theo nhu cầu của bạn
saved_song_name = None

# Biến toàn cục hoặc lưu vào database/file tùy theo nhu cầu của bạn
saved_song_name = None
latest_recognized_song = {}

def recognize(request):
    global latest_recognized_song  # Để có thể lưu song_name vào biến toàn cục
    if request.method == 'POST':
        print('Recognize endpoint hit')  # Debugging statement
        data = json.loads(request.body)
        seconds = data.get('seconds', 5)
        
        print(f'Calling recognize-from-microphone.py with {seconds} seconds')  # Debugging statement
        result = subprocess.run(['python', 'audio-fingerprint-identifying-python/recognize-from-microphone.py', '-s', str(seconds)], capture_output=True, text=True)
        
        print(f'Subprocess output: {result.stdout}')  # Debugging statement
        print(f'Subprocess error: {result.stderr}')  # Debugging statement
        
        if result.returncode != 0:
            return JsonResponse({"error": "Subprocess failed"}, status=500)

        try:
            # Tìm dòng có chứa JSON
            lines = result.stdout.splitlines()
            song_found = False  # Biến đánh dấu xem có nhận diện được hay không

            for line in lines:
                if '"song_name"' in line:
                    output = json.loads(line)
                    song_name = output.get("song_name")  # Lấy song_name từ kết quả
                    saved_song_name = song_name  # Lưu song_name vào biến toàn cục
                    
                    # Search for additional song info
                    song_info = search_song_by_name(song_name)
                    latest_recognized_song = song_info  # Lưu thông tin bài hát vào biến
                    print(latest_recognized_song)
                    
                    print(f"Song recognized: {saved_song_name}")  # In ra tên bài hát đã nhận diện
                    song_found = True  # Đã nhận diện được bài hát
                    return JsonResponse({
                        "track_name": latest_recognized_song.get("track_name"),
                        "artist_name": latest_recognized_song.get("artist_name"),
                        "album_image": latest_recognized_song.get("album_image"),
                        "song_id": latest_recognized_song.get("song_id"),
                    })

            # Nếu không tìm thấy "song_name" trong kết quả
            if not song_found:
                saved_song_name = "Undetified"  # Lưu lại trạng thái không nhận diện được
                print("Song could not be recognized: Undetified")  # In ra thông báo không nhận diện được
                return JsonResponse({"error": "Song name not found"}, status=500)
        except json.JSONDecodeError:
            print(f'Failed to parse output: {result.stdout}')  # Log the output for debugging
            return JsonResponse({"error": "Failed to parse recognition result"}, status=500)

# Kiểm tra nếu song_name đã được lưu
def check_song_name():
    if saved_song_name:
        print(f"Last recognized song: {saved_song_name}")
    else:
        print("No song has been recognized yet.")

@register.filter
def format_duration(value):
    total_seconds = int(value) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"

def search_song_by_name(song_name):
    sp = Spotify(auth_manager=SpotifyClientCredentials(
        client_id="8ea6321dd0e14815a75db4af02ba3a7b",
        client_secret="62ac40dff1a947de92df5df18b55312b"
    ))
    
    results = sp.search(q=song_name, type='track', limit=1, offset=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        song_id = track['id']
        track_name = track['name']
        artist_name = track['artists'][0]['name'] if track['artists'] else None
        album_image = track['album']['images'][0]['url'] if track['album']['images'] else None
        return {"song_id": song_id, "artist_name": artist_name, "album_image": album_image, "track_name": track_name}
    else:
        return {"error": "Song not found"}

def get_song_info(request):
    song_name = request.GET.get('song_name')
    if song_name:
        song_info = search_song_by_name(song_name)
        return JsonResponse(song_info)
    else:
        return JsonResponse({"error": "No song name provided"})
    
#def spotify_callback(request):
    code = request.GET.get('code')
    scope = 'user-top-read'
    sp_oauth = SpotifyOAuth(
        client_id="8ea6321dd0e14815a75db4af02ba3a7b",
        client_secret="62ac40dff1a947de92df5df18b55312b",
        redirect_uri="http://localhost:8000/callback",
        scope=scope
    )
    
    token_info = sp_oauth.get_access_token(code)
    if token_info:
        request.session['token_info'] = token_info
        return redirect('index')
    else:
        return HttpResponse('Failed to get token')