from collections import defaultdict

from PyQt6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from PyQt6.QtCore import QDate, QMargins, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QListWidget, QListWidgetItem, QSpinBox, QSplitter,
    QTabWidget, QToolTip, QVBoxLayout, QWidget,
)

from db_units.reports import Reports
from logic_units.formatting import rubles
from ui_units.widgets import Table, action, combo, day_edit, iso_date, label, surface, tell

METRICS = {"revenue": "Оплаченная выручка", "orders": "Заказы", "units": "Количество единиц"}
PERIODS = {"day": "По дням", "week": "По неделям", "month": "По месяцам", "year": "По годам"}


def value_text(value, metric):
    return rubles(value) if metric == "revenue" else str(value)


class MetricChart(QChartView):
    def __init__(self):
        super().__init__()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setMinimumHeight(210)

    def plot(self, pairs, metric):
        chart = QChart()
        chart.setBackgroundBrush(QBrush(QColor("#fffdf8")))
        chart.setBackgroundRoundness(0)
        chart.setMargins(QMargins(11, 10, 14, 6))
        chart.legend().hide()
        if not pairs:
            chart.setTitle("За выбранный период данных нет")
        else:
            captions, values = zip(*pairs)
            plot_values = [value / 100 if metric == "revenue" else value for value in values]
            bars = QBarSet(METRICS[metric])
            bars.append(plot_values)
            bars.setColor(QColor("#783b4b" if metric == "revenue" else "#92674e"))
            bars.setBorderColor(QColor("#783b4b" if metric == "revenue" else "#92674e"))
            bars.hovered.connect(
                lambda on, index: QToolTip.showText(
                    QCursor.pos(), f"{captions[index]}  ·  {value_text(values[index], metric)}", self
                ) if on else QToolTip.hideText()
            )
            series = QBarSeries()
            series.setBarWidth(0.57)
            series.append(bars)
            chart.addSeries(series)
            axis_x = QBarCategoryAxis()
            axis_x.append(list(captions))
            if len(pairs) >= 9:
                axis_x.setLabelsAngle(-32)
            axis_x.setGridLineVisible(False)
            axis_y = QValueAxis()
            axis_y.setLabelFormat("%.0f")
            axis_y.setRange(0, max(5, max(plot_values) * 1.08))
            axis_y.setTickCount(6)
            axis_y.applyNiceNumbers()
            axis_y.setGridLinePen(QPen(QColor("#eee5da")))
            for axis in (axis_x, axis_y):
                axis.setLabelsFont(QFont("Golos Text", 8))
                axis.setLabelsColor(QColor("#655650"))
                axis.setLinePenColor(QColor("#e4d9cb"))
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)

        previous = self.chart()
        self.setChart(chart)
        if previous:
            previous.deleteLater()


def range_fields(row, days=30):
    first = day_edit(QDate.currentDate().addDays(-days + 1))
    last = day_edit()
    row.addWidget(label("С"))
    row.addWidget(first)
    row.addWidget(label("по"))
    row.addWidget(last)
    return first, last


class ChartsPage(QWidget):
    def __init__(self, reports):
        super().__init__()
        self.reports = reports
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 15)
        layout.setSpacing(9)
        row = QHBoxLayout()
        self.mode = combo({"sales": "Динамика продаж", "revenue": "Выручка по периодам", "groups": "По категориям"})
        self.mode.setAccessibleName("Вид графика")
        row.addWidget(self.mode)
        self.first, self.last = range_fields(row)
        row.addStretch()
        layout.addLayout(row)

        options = QHBoxLayout()
        self.metric = combo(METRICS)
        self.metric.setAccessibleName("Показатель")
        self.period = combo(PERIODS, "week")
        self.period.setAccessibleName("Группировка")
        options.addWidget(self.metric)
        options.addWidget(self.period)
        options.addWidget(action("Показать", self.refresh, "primary"))
        options.addStretch()
        layout.addLayout(options)

        self.caption = label("", "strong")
        layout.addWidget(self.caption)
        self.chart = MetricChart()
        self.table = Table(("Период / категория", "Подкатегория", "Заказы", "Единиц", "Оплачено"),
                           (170, 125, 75, 70))
        self.table.setMinimumHeight(105)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.chart)
        split.addWidget(self.table)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)
        self.mode.currentIndexChanged.connect(self.refresh)
        self.period.currentIndexChanged.connect(self.refresh)
        self.metric.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self):
        mode = self.mode.currentData()
        metric = "revenue" if mode == "revenue" else self.metric.currentData()
        self.period.setVisible(mode == "revenue")
        self.metric.setVisible(mode != "revenue")
        first, last = iso_date(self.first), iso_date(self.last)
        if last < first:
            self.caption.setText("Конечная дата должна быть не раньше начальной.")
            self.chart.plot([], metric)
            self.table.fill([])
            return

        if mode == "groups":
            rows = self.reports.categories(first, last)
            if metric == "orders":
                pairs = [(row["subcategory"], row["orders"]) for row in rows]
            else:
                values = defaultdict(int)
                for row in rows:
                    values[row["label"]] += row[metric]
                pairs = list(values.items())
        elif mode == "revenue":
            rows = self.reports.revenue(self.period.currentData(), first, last)
            pairs = [(row["label"], row[metric]) for row in rows]
        else:
            rows = self.reports.sales(first, last)
            pairs = [(row["label"], row[metric]) for row in rows]
        heading = METRICS[metric]
        if len(pairs) > 20:
            heading += " · последние 20 периодов"
        self.caption.setText(heading)
        displayed = pairs[-20:]
        if mode == "sales" or (mode == "revenue" and self.period.currentData() == "day"):
            same_year = first[:4] == last[:4]
            displayed = [(QDate.fromString(key, "yyyy-MM-dd").toString(
                "dd.MM" if same_year else "dd.MM.yy"
            ), value) for key, value in displayed]
        self.chart.plot(displayed, metric)
        self.table.setColumnHidden(1, mode != "groups")
        self.table.fill([
            (row["label"], row.get("subcategory", ""), row["orders"], row["units"], rubles(row["revenue"]))
            for row in rows
        ])


class SummaryReports(QWidget):
    def __init__(self, reports):
        super().__init__()
        self.reports = reports
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 15)
        split = QSplitter(Qt.Orientation.Vertical)

        daily = QWidget()
        daily_layout = QVBoxLayout(daily)
        daily_layout.setContentsMargins(0, 0, 0, 4)
        daily_controls = QHBoxLayout()
        daily_controls.addWidget(label("Отчёт за день", "strong"))
        self.day = day_edit()
        daily_controls.addWidget(self.day)
        daily_controls.addWidget(action("Сформировать", self.refresh_daily, "secondary"))
        daily_controls.addStretch()
        daily_layout.addLayout(daily_controls)
        self.daily_table = Table(("Показатель", "Значение"), (310,))
        daily_layout.addWidget(self.daily_table, 1)
        split.addWidget(daily)

        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 4, 0, 0)
        row = QHBoxLayout()
        row.addWidget(label("Топ товаров", "strong"))
        row.addStretch()
        row.addWidget(label("Период, дней"))
        self.days = QSpinBox()
        self.days.setRange(1, 365)
        self.days.setValue(30)
        row.addWidget(self.days)
        row.addWidget(label("Строк"))
        self.limit = QSpinBox()
        self.limit.setRange(1, 50)
        self.limit.setValue(10)
        row.addWidget(self.limit)
        row.addWidget(action("Показать", self.refresh_top, "secondary"))
        top_layout.addLayout(row)
        self.top_table = Table(("Артикул", "Товар", "Категория", "Единиц", "Заказов", "Оплачено"),
                               (88, 181, 124, 64, 70))
        top_layout.addWidget(self.top_table, 1)
        split.addWidget(top)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        layout.addWidget(split)
        self.refresh_daily()
        self.refresh_top()

    def refresh_daily(self):
        result = self.reports.daily(iso_date(self.day))
        self.daily_table.fill([
            ("Заказы", result["orders"]),
            ("Оплаченная выручка", rubles(result["revenue"])),
            ("Средний оплаченный чек", rubles(round(result["average"]))),
            ("Покупатели", result["clients"]),
            ("Товаров в заказах", result["units"]),
            ("Новые заказы", result["new_orders"]),
            ("Доставленные заказы", result["completed"]),
        ])

    def refresh_top(self):
        self.top_table.fill([
            (row["sku"], row["name"], row["category"], row["units"], row["orders"], rubles(row["revenue"]))
            for row in self.reports.top(self.limit.value(), self.days.value())
        ])


class ComparisonPage(QWidget):
    def __init__(self, db, reports):
        super().__init__()
        self.reports = reports
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 15)
        row = QHBoxLayout()
        self.first, self.last = range_fields(row)
        self.metric = combo(METRICS)
        row.addWidget(self.metric)
        row.addWidget(action("Сравнить", self.refresh, "primary"))
        row.addStretch()
        layout.addLayout(row)

        content = QHBoxLayout()
        left = surface()
        left.setFixedWidth(226)
        picker = QVBoxLayout(left)
        picker.addWidget(label("Выбери модели", "strong"))
        self.products = QListWidget()
        self.products.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        products = db.products()
        featured = {"EL-W01", "EL-M01", "EL-A01"}
        for product in products:
            item = QListWidgetItem(f"{product['sku']}  ·  {product['name']}")
            item.setData(Qt.ItemDataRole.UserRole, product["sku"])
            item.setToolTip(product["name"])
            self.products.addItem(item)
            if product["sku"] in featured:
                item.setSelected(True)
        picker.addWidget(self.products, 1)
        content.addWidget(left)
        result = QSplitter(Qt.Orientation.Vertical)
        self.chart = MetricChart()
        self.table = Table(("Артикул", "Товар", "Заказы", "Единиц", "Оплачено"), (86, 156, 70, 64))
        result.addWidget(self.chart)
        result.addWidget(self.table)
        result.setStretchFactor(0, 2)
        result.setStretchFactor(1, 1)
        content.addWidget(result, 1)
        layout.addLayout(content, 1)
        self.metric.currentIndexChanged.connect(lambda: self.refresh(quiet=True))
        self.refresh(quiet=True)

    def refresh(self, quiet=False):
        metric = self.metric.currentData()
        selected = [item.data(Qt.ItemDataRole.UserRole) for item in self.products.selectedItems()]
        first, last = iso_date(self.first), iso_date(self.last)
        if last < first or not selected:
            if not quiet:
                tell(self, "Сравнение", "Проверь диапазон дат и выбери хотя бы одну модель.")
            self.chart.plot([], metric)
            self.table.fill([])
            return
        rows = self.reports.compare(selected, first, last)
        self.chart.plot([(row["label"], row[metric]) for row in rows], metric)
        self.table.fill([
            (row["label"], row["name"], row["orders"], row["units"], rubles(row["revenue"]))
            for row in rows
        ])


class AnalyticsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        reports = Reports(db)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 25)
        layout.setSpacing(12)
        layout.addWidget(label("Аналитика", "title"))
        tabs = QTabWidget()
        tabs.addTab(ChartsPage(reports), "Графики")
        tabs.addTab(SummaryReports(reports), "Отчёты")
        tabs.addTab(ComparisonPage(db, reports), "Сравнение")
        layout.addWidget(tabs, 1)
