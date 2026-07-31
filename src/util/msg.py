class Message:
    MSG_START: str = "数据统计开始"
    MSG_END: str = "数据统计结束"

    MSG_FILE_WRITE_ERROR: str = (
        '<font color="red">Excel文件写入失败, 请先关闭%s文件</font>'
    )

    MSG_LABEL: str = "警告"
    MSG_NO_FILE_SELECT: str = "请选择待统计log!"
    MSG_COORDINATE_NAME_EMPTY: str = "坐标名称为空！"
    MSG_COORDINATE_TYPE_ERROR: str = "坐标类型错误！"
    MSG_COORDINATE_RANGE_ERROR: str = "坐标范围错误！"
    MSG_COORDINATE_DELETE: str = '确定删除坐标信息: "%s"?'
    MSG_POINT_INVALID: str = "参考无效！"
    MSG_DATE_INVALID: str = "REPORT-UTC.json日期格式错误(格式：YYYYMMDD)！"
    MSG_DATE_EMPTY: str = "REPORT-UTC.json未指定日期！"
    MSG_TIME_EMPTY: str = "REPORT-UTC.json未指定场景！"
    MSG_TIME_INVALID: str = "REPORT-UTC.json时间格式错误(格式：HHMMSS)！"
    MSG_REPORT_JSON_INVALID: str = "REPORT-UTC.json格式错误！"
    MSG_REPORT_JSON_NOT_FOUND: str = "REPORT-UTC.json未找到！"
    MSG_REPORT_JSON_EMPTY: str = "REPORT-UTC.json未指定！"


class DialogMessage:
    SELECTED_FOLDER: str = "选取文件夹"
    SELECTED_FILE: str = "选取文件"
