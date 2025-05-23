import datetime
import logging

from CogEditor.models import AgreedStatus, Application, ParticipatoryRole
from django.core.exceptions import ValidationError
from django.db import models

logger = logging.getLogger(__name__)


class Rule(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Наименование правила",
    )
    description = models.TextField(verbose_name="Описание правила")
    priority = models.IntegerField(
        default=1,
        verbose_name="Приоритет выполнения",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активно",
    )

    # Параметры условия
    condition_type = models.CharField(
        max_length=20,
        choices=[
            (
                "date_compare",
                "Сравнение дат",
            ),
            (
                "role_check",
                "Проверка роли",
            ),
            (
                "text_length",
                "Длина текста",
            ),
            (
                "combined",
                "Комбинированное условие",
            ),
        ],
        verbose_name="Тип условия",
    )

    # Параметры для разных типов условий
    days_threshold = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Порог дней",
    )
    role_id = models.ManyToManyField(
        ParticipatoryRole,
        blank=True,
        verbose_name="Роли",
    )

    min_text_length = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Минимальная длина текста",
    )

    # Результирующий статус
    new_status = models.ForeignKey(
        AgreedStatus,
        on_delete=models.CASCADE,
        verbose_name="Новый статус",
    )

    def evaluate(self, application):
        """Применяет правило к заявке и возвращает True, если условие
        выполнено"""
        if not self.is_active:
            return False

        try:
            if self.condition_type == "date_compare":
                if self.days_threshold is None:
                    return False

                # Получаем все даты мероприятий
                event_schedules = application.event_schedule.all()
                if not event_schedules.exists():
                    return False

                from django.utils import timezone

                # Преобразуем дату подачи заявки в осознанную (aware) дату,
                # если необходимо
                subm_date = application.subm_date
                if timezone.is_naive(subm_date):
                    subm_date = timezone.make_aware(subm_date)

                # Вычисляем пороговую дату
                threshold_date = subm_date + datetime.timedelta(
                    days=self.days_threshold
                )

                # Проверяем все даты мероприятий
                for schedule in event_schedules:
                    if schedule.start is None:
                        continue

                    # Приводим дату мероприятия к тому же типу временной зоны
                    event_date = schedule.start
                    if timezone.is_naive(event_date):
                        event_date = timezone.make_aware(event_date)

                    # Если хотя бы одно мероприятие раньше пороговой даты -
                    # правило не выполняется
                    if event_date >= threshold_date:
                        return False

                return True

            elif self.condition_type == "role_check":
                if not self.role_id.exists():
                    return False
                role_ids = self.role_id.values_list("id", flat=True)
                return application.roles.filter(id__in=role_ids).exists()

            elif self.condition_type == "text_length":
                if self.min_text_length is None:
                    return False
                return len(application.e_description) < self.min_text_length

            elif self.condition_type == "combined":
                # Инициализация флагов
                date_ok = role_ok = text_ok = True

                # Проверка дат (исправленная часть)
                if self.days_threshold is not None:
                    if application.subm_date is None:
                        date_ok = False
                    else:
                        from django.utils import timezone

                        # Нормализуем дату подачи заявки
                        subm_date = application.subm_date
                        if timezone.is_naive(subm_date):
                            subm_date = timezone.make_aware(subm_date)

                        threshold_date = subm_date + datetime.timedelta(
                            days=self.days_threshold
                        )

                        # Проверяем все расписания
                        has_valid_dates = False
                        for schedule in application.event_schedule.all():
                            if schedule.start is None:
                                continue

                            event_date = schedule.start
                            if timezone.is_naive(event_date):
                                event_date = timezone.make_aware(event_date)

                            # Приводим обе даты к UTC для корректного сравнения
                            event_date_utc = event_date.astimezone(
                                datetime.timezone.utc
                            )
                            threshold_date_utc = threshold_date.astimezone(
                                datetime.timezone.utc
                            )

                            if event_date_utc >= threshold_date_utc:
                                date_ok = False
                                break

                            has_valid_dates = True

                        date_ok = date_ok and has_valid_dates
                        # Проверка ролей
                    if self.role_id.exists():  # Упрощенная проверка
                        role_ok = application.roles.filter(
                            id__in=self.role_id.values_list("id", flat=True)
                        ).exists()

                # Проверка длины текста
                if self.min_text_length is not None:
                    text_ok = (
                        len(application.e_description or "")
                        < self.min_text_length
                    )

                return date_ok and role_ok and text_ok

        except (TypeError, ValueError):
            raise TypeError
            return False

        return False

    def clean(self):
        if (
            self.condition_type == "date_compare"
            and self.days_threshold is None
        ):
            raise ValidationError(
                "Для сравнения дат необходимо указать порог дней"
            )
        if self.condition_type == "role_check" and self.role_id is None:
            raise ValidationError(
                "Для проверки роли необходимо указать ID роли"
            )
        if (
            self.condition_type == "text_length"
            and self.min_text_length is None
        ):
            raise ValidationError(
                "Для проверки длины текста необходимо указать минимальную"
                " длину"
            )

    class Meta:
        verbose_name = "правило"
        verbose_name_plural = "правила"
        ordering = ["-priority", "name"]


class RuleEngine:
    """Применяет все активные правила к заявке"""

    @staticmethod
    def apply_rules_to_application(
        application,
    ):
        settings = ClassificationSettings.objects.first()
        change_status = (
            settings.change_status_on_classify if settings else True
        )

        rules = Rule.objects.filter(is_active=True).order_by("-priority")

        for rule in rules:
            try:
                if rule.evaluate(application):
                    # Возвращаем новый статус и обновляем заявку
                    if change_status:
                        application.status = rule.new_status
                        application.save()
                    return rule.new_status

            except Exception as e:
                logger.error(
                    f"Error evaluating rule {rule.id} for application "
                    f"{application.id}: {str(e)}"
                )
                continue

        # Возвращаем исходный статус при ошибках или если правила не сработали
        return application.status

    @staticmethod
    def batch_apply_rules():
        """Применяет правила ко всем заявкам и возвращает результаты"""
        results = []
        applications = Application.objects.all().reverse()

        for app in applications:
            new_status = RuleEngine.apply_rules_to_application(app)
            results.append(
                {
                    "application": app,
                    "current_status": app.status,
                    "new_status": new_status,
                    "status_changed": new_status != app.status,
                }
            )

        return results


class ClassificationSettings(models.Model):
    change_status_on_classify = models.BooleanField(
        default=True, verbose_name="Изменять статус при классификации"
    )

    class Meta:
        verbose_name = "Настройка классификации"
        verbose_name_plural = "Настройки классификации"

    def __str__(self):
        return "Настройки автоматической классификации"
