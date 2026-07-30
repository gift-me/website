from datetime import datetime

from .models import UserProfile


def save_profile_from_request(user, request, mark_complete=True):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    username = request.POST.get("username", "").strip()
    display_name = request.POST.get("display_name", "").strip()
    birthday_raw = request.POST.get("birthday_date", "").strip()

    if username:
        if UserProfile.objects.filter(username=username).exclude(pk=profile.pk).exists():
            return "This username is already taken."
        profile.username = username

    if display_name:
        profile.display_name = display_name

    if birthday_raw:
        try:
            profile.birthday_date = datetime.strptime(birthday_raw, "%Y-%m-%d").date()
        except ValueError:
            return "Enter a valid birthday date."

    if request.FILES.get("profile_picture"):
        profile.profile_picture = request.FILES["profile_picture"]

    if mark_complete:
        profile.setup_completed = True

    profile.save()
    return None
