from jmcomic import *
from jmcomic.cl import JmcomicUI

# 下方填入你要下载的本子的id，一行一个，每行的首尾可以有空白字符
jm_albums = '''
1085899 
1097276 
1093337 
1046228 
1092943 
1091508 
636679 
1091465 
1062044 
1086711 
1079725 
1078258 
1065810 
1073070 
1019997 
1071119 
388381 
1040999 
1063819 
1066410 
1052919 
573966 
1061008 
1044352 
572049 
1045164 
1048366 
1037778 
1042555 
1045524 
575036 
620560 
1026835 
1029119 
112952 
1029520 
287188 
524328 
1026275
411578 
431899 
468941 
404551 
560008 
609877 
1020551 
483335 
401625 
643289 
604146 
466431 
1014620 
1018560 
1014476 
631111 
513122 
412277 
308812 
463445 
540889 
649688 
642381 
549758 
1068 
458429 
446054 
545509 
650138 
1013114 
650884 
652027 
650298 
651747 
650475 
317491 
643763 
636703 
319724 
149123 
454444 
607341 
505694 
9621 
511737 
561435 
449842 
536014 
624376 
615110 
308747 
333217 
418958 
522683 
613940 
526312 
2330 
608679 
604781 
604109 
418972 
546429 
595248 
597511 
451585 
590272 
506368 
205606 
557543 
580020 
438299 
431421 
563734 
345016 
574889 
209827 
216625 
14303 
570120 
184704 
356965 
189216 
150528 
150217 
150321 
38784 
546474 
545460 
551672 
534683 
564065 
471471 
455414 
455017 
567944 
484109 
337886 
459254 
484690 
561956 
567736 
313930 
436318 
496902 
536319 
567255 
444521 
559994 
548402 
550715 
551251 
17534 
526061 
558842 
151965 
30009 
87651 
116506 
467988 
543070 
357675 
401408 
494229 
84034 
362063 
484110 
313490 
533246 
524895 
522346 
508628 
512637 
472790 
285091 
514448 
480841 
418470 
287365 
452738 
475696 
479426 
470704 
457888 
566986 
454851 
439824 
469450 
470838 
466370 
466420 
418987 
462292 
461611 
462257 
465021 
464018 
287395 
324930 
457082 
455878 
447294 
456376 
454212 
332711 
449582 
448042 
446738 
419658 
419039 
444532 
419045 
438243 
438391 
437212 
438570 
439516 
174044 
179986 
430379 
102658 
400912 
428661 
427274 
425453 
422847 
422846 
423216 
425210 
424109 
424821 
423726 
419395 
419416 
419674 
419298 
418770 
419116 
416888 
416688 
333646 
602132 
414196 
414797 
415274 
415296 
415579 
415761 
414108 
414385 
214271 
413828 
413140 
413376 
411998 
7734 
3116 
40549 
43135 



'''

# 单独下载章节
jm_photos = '''



'''


def env(name, default, trim=('[]', '""', "''")):
    import os
    value = os.getenv(name, None)
    if value is None or value == '':
        return default

    for pair in trim:
        if value.startswith(pair[0]) and value.endswith(pair[1]):
            value = value[1:-1]

    return value


def get_id_set(env_name, given):
    aid_set = set()
    for text in [
        given,
        (env(env_name, '')).replace('-', '\n'),
    ]:
        aid_set.update(str_to_set(text))

    return aid_set


def main():
    album_id_set = get_id_set('JM_ALBUM_IDS', jm_albums)
    photo_id_set = get_id_set('JM_PHOTO_IDS', jm_photos)

    helper = JmcomicUI()
    helper.album_id_list = list(album_id_set)
    helper.photo_id_list = list(photo_id_set)

    option = get_option()
    helper.run(option)
    option.call_all_plugin('after_download')


def get_option():
    # 读取 option 配置文件
    option = create_option(os.path.abspath(os.path.join(__file__, '../../assets/option/option_workflow_download.yml')))

    # 支持工作流覆盖配置文件的配置
    cover_option_config(option)

    # 把请求错误的html下载到文件，方便GitHub Actions下载查看日志
    log_before_raise()

    return option


def cover_option_config(option: JmOption):
    dir_rule = env('DIR_RULE', None)
    if dir_rule is not None:
        the_old = option.dir_rule
        the_new = DirRule(dir_rule, base_dir=the_old.base_dir)
        option.dir_rule = the_new

    impl = env('CLIENT_IMPL', None)
    if impl is not None:
        option.client.impl = impl

    suffix = env('IMAGE_SUFFIX', None)
    if suffix is not None:
        option.download.image.suffix = fix_suffix(suffix)


def log_before_raise():
    jm_download_dir = env('JM_DOWNLOAD_DIR', workspace())
    mkdir_if_not_exists(jm_download_dir)

    def decide_filepath(e):
        resp = e.context.get(ExceptionTool.CONTEXT_KEY_RESP, None)

        if resp is None:
            suffix = str(time_stamp())
        else:
            suffix = resp.url

        name = '-'.join(
            fix_windir_name(it)
            for it in [
                e.description,
                current_thread().name,
                suffix
            ]
        )

        path = f'{jm_download_dir}/【出错了】{name}.log'
        return path

    def exception_listener(e: JmcomicException):
        """
        异常监听器，实现了在 GitHub Actions 下，把请求错误的信息下载到文件，方便调试和通知使用者
        """
        # 决定要写入的文件路径
        path = decide_filepath(e)

        # 准备内容
        content = [
            str(type(e)),
            e.msg,
        ]
        for k, v in e.context.items():
            content.append(f'{k}: {v}')

        # resp.text
        resp = e.context.get(ExceptionTool.CONTEXT_KEY_RESP, None)
        if resp:
            content.append(f'响应文本: {resp.text}')

        # 写文件
        write_text(path, '\n'.join(content))

    JmModuleConfig.register_exception_listener(JmcomicException, exception_listener)


if __name__ == '__main__':
    main()
