# shared PyInstaller config for EX SPORTS SFC 27
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
import os, glob
DROP = ('avcodec', 'avformat', 'avutil', 'swresample', 'swscale', 'libp3ffmpeg', 'fmod', 'assimp', 'ptloader',
        'bullet', 'pandaode', 'pandaai', 'vrpn', 'p3vision', 'pandadx9', 'd3dx9', 'cgd3d9', 'pandaphysics', 'pandafx')
BINS = [x for x in collect_dynamic_libs('panda3d') if not any(k in os.path.basename(x[0]).lower() for k in DROP)]
DATAS = collect_data_files('panda3d', includes=['etc/*'])
ASSETS = [(f, 'assets') for f in ('assets/title.jpg', 'assets/icon.ico', 'assets/icon.png', 'assets/ui_font.ttf', 'assets/ui_plain.ttf', 'assets/THIRD_PARTY.txt', 'assets/intro_logo.png', 'assets/menu_bg.jpg')]
ASSETS += [('assets/sfx', 'assets/sfx'), ('assets/tex', 'assets/tex')]
HIDDEN = ['panda3d.core', 'panda3d.direct', 'direct.showbase.ShowBase', 'direct.gui.DirectGui',
          'xs_geom', 'xs_ui', 'xs_shaders', 'xs_mesh', 'xs_person', 'xs_avatar', 'xs_data', 'xs_net', 'xs_sfc', 'xs_online', 'xs_arena', 'xs_recorder', 'numpy']
EXCL = ['matplotlib', 'scipy', 'pandas', 'IPython', 'pytest', 'tkinter', 'PIL', 'cv2', 'wx', 'PyQt5', 'imageio_ffmpeg']
# v1.0.0.2 EX SPORTS RECORDER: bundled ffmpeg (imageio-ffmpeg's static Windows build with libx264 + AAC), run as a separate exe
try:
    import imageio_ffmpeg
    ASSETS += [(imageio_ffmpeg.get_ffmpeg_exe(), 'ffmpeg')]
except Exception as e:
    print('WARNING: ffmpeg not bundled:', e)
