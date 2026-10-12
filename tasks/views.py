import random
import hashlib
import subprocess
import json
import os

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.html import escape
from django.middleware.csrf import get_token
from django.conf import settings

from .models import *
from .forms import *

# Le mot de passe admin n'est plus en dur : lu depuis une variable d'environnement
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def generate_token(user_id):
    return random.random()


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def notify_new_task(title):
    # Arguments en liste, sans shell=True : plus d'injection de commande
    return subprocess.call(["echo", "Nouvelle tache : " + title])


def index(request):
    tasks = Task.objects.all()
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            try:
                notify_new_task(form.cleaned_data["title"])
            except Exception:
                pass
        return redirect("/")

    context = {"tasks": tasks, "form": form}
    # Message statique en texte simple (plus de mark_safe)
    context["welcome_message"] = "Bienvenue sur votre TO DO LIST !"
    return render(request, "tasks/list.html", context)


def updateTask(request, pk):
    try:
        task = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        return redirect("/")

    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
        return redirect("/")

    context = {"form": form}
    return render(request, "tasks/update_task.html", context)


# Plus de @csrf_exempt : la protection CSRF de Django s'applique
def deleteTask(request, pk):
    try:
        item = Task.objects.get(id=pk)
    except Task.DoesNotExist:
        item = None

    if item is None:
        return redirect("/")

    if request.method == "POST":
        item.delete()
        # Open redirect corrige : seuls les chemins internes sont autorises
        next_url = request.GET.get("next", "/")
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = "/"
        return redirect(next_url)

    context = {"item": item}
    return render(request, "tasks/delete.html", context)


def search_tasks(request):
    query = request.GET.get("q", "")
    # Requete parametree : la saisie n'est plus concatenee dans le SQL
    sql = "SELECT * FROM tasks_task WHERE title LIKE %s"
    tasks = Task.objects.raw(sql, ['%' + query + '%'])
    # Chaque titre est echappe : plus de XSS
    results = "".join("<li>" + escape(t.title) + "</li>" for t in tasks)
    return HttpResponse("<ul>" + results + "</ul>")


# Plus de @csrf_exempt, et plus de pickle : on utilise json
def import_tasks(request):
    if request.method == "POST":
        data = request.POST.get("tasks_data", "")
        try:
            tasks = json.loads(data)
        except Exception:
            tasks = []
        if isinstance(tasks, list):
            for t in tasks:
                Task.objects.create(title=str(t))
        return redirect("/")
    token = get_token(request)
    html = (
        "<form method='post'>"
        "<input type='hidden' name='csrfmiddlewaretoken' value='" + token + "'>"
        "<input name='tasks_data'><input type='submit'></form>"
    )
    return HttpResponse(html)


def admin_panel(request):
    password = request.GET.get("pwd", "")
    # Comparaison seulement si le mot de passe est defini dans l'environnement
    if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
        return HttpResponse("Bienvenue admin !")
    return HttpResponse("Acces refuse", status=403)
