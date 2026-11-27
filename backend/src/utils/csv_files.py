import csv
import io
import re


def read_rows(text, columns):
    source = csv.DictReader(io.StringIO(text.removeprefix('\ufeff'), newline=''), strict=True)
    try:
        if source.fieldnames != columns:
            raise ValueError('CSV 列名和顺序应为 ' + ', '.join(columns))
        rows = []
        for row in source:
            if None in row or None in row.values():
                raise ValueError(f'CSV 第 {source.line_num} 行列数有误')
            rows.append(row)
            if len(rows) > 5000:
                raise ValueError('单个台账最多导入 5000 行')
    except csv.Error as error:
        raise ValueError('CSV 格式有误，请核对引号和分列') from error
    if not rows:
        raise ValueError('CSV 没有记录')
    return rows


def spreadsheet_cell(value):
    if isinstance(value, str) and (re.match(r'\s*[=+\-@]', value) or value.startswith(('\t', '\r', '\n'))):
        return "'" + value
    return value


def write_rows(columns, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: spreadsheet_cell(value) for key, value in row.items()})
    return '\ufeff' + buffer.getvalue()
