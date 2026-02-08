from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import CheckConstraint, UniqueConstraint, Q
from django.utils import timezone


class Lobby(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    password = models.CharField(max_length=50, null=True, blank=True, default=None)
    members = models.ManyToManyField("authentication.CustomUser", through="Membership")
    game_history = models.OneToOneField("GameHistory", on_delete=models.CASCADE, null=True, blank=True, default=None)
    lobby_lvl = models.PositiveIntegerField(default=None, null=True, blank=True)
    is_block = models.BooleanField(null=True, blank=True, default=None)
    bet = models.IntegerField(null=True, default=None)
    match_id = models.CharField(blank=True, max_length=100, null=True)

    task_id = models.CharField(blank=True, max_length=100, null=True)

    datetime_create = models.DateTimeField(default=timezone.now)
    datetime_start_game = models.DateTimeField(null=True, blank=True)
    datetime_finish_game = models.DateTimeField(null=True, blank=True)
    position = models.IntegerField(null=True, default=None)

    LOBBY_STATUS = (
        ("Created", "Created"),
        ("Pending", "Pending"),
        ("Game started", "Game started"),
        ("Finished", "Finished"),
        ("Error", "Error"),
    )
    status = models.CharField(default="Created", max_length=100, choices=LOBBY_STATUS)

    MODS = (
        (2, '1v1'),
        (10, '5v5'),
    )
    slots = models.IntegerField(default=2, choices=MODS)

    GAME_MODS = (
        ("All Pick", 'All Pick'),
        ("1v1 Solo Mid", '1v1 Solo Mid'),
        ("Captains Mode", 'Captains Mode'),
    )
    game_mode = models.CharField(default="All Pick", max_length=100, choices=GAME_MODS)

    def __str__(self):
        return self.name

    @property
    def is_slots_gte_memberships(self):
        return self.membership.count() <= self.slots

    @property
    def is_slots_lte_memberships(self):
        return self.membership.count() >= self.slots


class Membership(models.Model):
    user = models.ForeignKey("authentication.CustomUser", on_delete=models.CASCADE)
    lobby = models.ForeignKey(Lobby, on_delete=models.CASCADE, related_name='membership')
    team = models.CharField(max_length=1, choices=(('1', 'Team 1'), ('2', 'Team 2')), null=True, default='1')
    position = models.PositiveIntegerField(null=True, blank=True)
    status = models.BooleanField(default=False)
    leader = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} in lobby {self.lobby.name}"

    class Meta:
        ordering = ['team']


class Bot(models.Model):
    id = models.AutoField(primary_key=True)
    bot_name = models.CharField(max_length=150, null=True, default=None)
    bot_password = models.CharField(max_length=100, null=True, default=None)
    bot_status = models.BooleanField(default=False)

    def __str__(self):
        return self.bot_name


class PlayerInfo(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("authentication.CustomUser", on_delete=models.CASCADE)
    steam_id = models.CharField(null=True, blank=True, max_length=100)
    hero_id = models.IntegerField(null=True, blank=True)
    team = models.CharField(max_length=1, choices=(('1', 'Team 1'), ('2', 'Team 2')), null=True, default='1')
    game_team = models.CharField(max_length=50, null=True, default=None)
    game_name = models.CharField(max_length=200, null=True, default=None)
    rate = models.OneToOneField("Rating", null=True, blank=True, default=None, on_delete=models.SET_NULL)
    game_commission = models.FloatField(default=0.0, null=True, blank=True)

    def __str__(self):
        return f"{self.steam_id}___{self.game_name}"


class Rating(models.Model):
    id = models.AutoField(primary_key=True)
    rate = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    user = models.ForeignKey("authentication.CustomUser", on_delete=models.CASCADE)
    player_info = models.ForeignKey(PlayerInfo, on_delete=models.CASCADE, default=None)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            CheckConstraint(condition=Q(rate__range=(1, 5)), name='valid_rate'),
            UniqueConstraint(fields=['user', 'player_info'], name='rating_once')
        ]


class GameHistory(models.Model):
    id = models.AutoField(primary_key=True)
    lobby_link = models.ForeignKey(Lobby, on_delete=models.CASCADE)
    start_game = models.DateTimeField(auto_now_add=True)
    finish_game = models.DateTimeField(auto_now=True)
    result = models.CharField(max_length=50, null=True, default=None)
    players_info = models.ManyToManyField(PlayerInfo, blank=True, default=None)

    def __str__(self):
        return self.lobby_link.name
