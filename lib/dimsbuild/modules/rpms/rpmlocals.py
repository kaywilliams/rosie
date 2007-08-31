SCRIPT = ''' 
chmod +w /usr/share/gdm/defaults.conf
sed -i 's/^GraphicalTheme=[a-zA-Z]*$/GraphicalTheme=%s/g' /usr/share/gdm/defaults.conf
chmod -w /usr/share/gdm/defaults.conf
'''

RELEASE_NOTES_HTML = '''<html>
  <head>
  <style type="text/css">
  <!--
  body {
    background-color: %s;
    color: %s;
    font-family: sans-serif;
  }
  .center {
    text-align: center;
  }
  p {
    margin-top: 20%%;
  }
  -->
  </style>
  </head>
  <body>
  <h1>
    <p class="center">Welcome to %s!</p>
  </h1>
  </body>
</html>
'''

GDM_GREETER_THEME = ''' 
# This is not really a .desktop file like the rest, but it\'s useful to treat
# it as such
[GdmGreeterTheme]
Encoding=UTF-8
Greeter=%s.xml
Name=%s Theme
Description=%s Theme
Author=dimsbuild
Screenshot=background.png
'''

L_LOGOS = ''' 
<locals>
  <logos-entries>
    <logos version="0">
      <logo id="bootloader/grub-splash.xpm.gz">
        <location>/boot/grub/splash.xpm.gz</location>
      </logo>
      <logo id="bootloader/grub-splash.png">
        <width>640</width>
        <height>480</height>
        <location>/boot/grub/splash.png</location>
      </logo>
      <logo id="anaconda/syslinux-splash.png">
        <width>640</width>
        <height>300</height>
        <location>/usr/lib/anaconda-runtime/boot/syslinux-splash.png</location>
        <textmaxwidth>600</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>320</texthcenter>
      </logo>
      <logo id="anaconda/splashtolss.sh">
        <location>/usr/lib/anaconda-runtime/splashtolss.sh</location>
      </logo>
      <logo id="anaconda/anaconda_header.png">
        <width>800</width>
        <height>89</height>
        <location>/usr/share/anaconda/pixmaps/anaconda_header.png</location>
        <textmaxwidth>750</textmaxwidth>
        <textvcenter>45</textvcenter>
        <texthcenter>400</texthcenter>
      </logo>
      <logo id="anaconda/progress_first-lowres.png">
        <width>350</width>
        <height>224</height>
        <location>/usr/share/anaconda/pixmaps/progress_first-lowres.png</location>
        <textmaxwidth>300</textmaxwidth>
        <texthcenter>175</texthcenter>                
        <textvcenter>112</textvcenter>
        <gradient>True</gradient>
      </logo>
      <logo id="anaconda/progress_first.png">
        <width>507</width>
        <height>325</height>
        <location>/usr/share/anaconda/pixmaps/progress_first.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>250</texthcenter>
        <gradient>True</gradient>
      </logo>
      <logo id="anaconda/splash.png">
        <width>507</width>
        <height>388</height>
        <location>/usr/share/anaconda/pixmaps/splash.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>194</textvcenter>
        <texthcenter>250</texthcenter>
        <gradient>True</gradient>        
      </logo>
      <logo id="kde-splash/BlueCurve/Theme.rc">
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/Theme.rc</location>
      </logo>
      <logo id="kde-splash/BlueCurve/splash_active_bar.png">
        <width>400</width>
        <height>61</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_active_bar.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>30</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_bottom.png">
        <width>400</width>
        <height>16</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_bottom.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>8</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_inactive_bar.png">
        <width>400</width>
        <height>61</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_inactive_bar.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>30</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_top.png">
        <width>400</width>
        <height>244</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_top.png</location>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>112</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="firstboot/firstboot-header.png">
        <width>800</width>
        <height>58</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-header.png</location>
        <textmaxwidth>750</textmaxwidth>
        <textvcenter>25</textvcenter>
        <texthcenter>400</texthcenter>
        <highlight>True</highlight>
      </logo>
      <logo id="firstboot/firstboot-left.png">
        <width>160</width>
        <height>600</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-left.png</location>
        <highlight>True</highlight>
      </logo>
      <logo id="firstboot/shadowman-round-48.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/firstboot/pixmaps/shadowman-round-48.png</location>
      </logo>
      <logo id="firstboot/splash-small.png">
        <width>550</width>
        <height>200</height>
        <location>/usr/share/firstboot/pixmaps/splash-small.png</location>
        <textmaxwidth>530</textmaxwidth>
        <textvcenter>100</textvcenter>
        <texthcenter>275</texthcenter>
        <highlight>True</highlight>
      </logo>
      <logo id="firstboot/workstation.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/firstboot/pixmaps/workstation.png</location>
      </logo>
      <logo id="gnome-screensaver/lock-dialog-system.glade">
        <location>/usr/share/gnome-screensaver/lock-dialog-system.glade</location>
      </logo>
      <logo id="redhat-pixmaps/rhad.png">
        <width>291</width>
        <height>380</height>
        <location>/usr/share/pixmaps/redhat/rhad.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpm.tif">
        <width>801</width>
        <height>512</height>
        <location>/usr/share/pixmaps/redhat/rpm.tif</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-200.png">
        <width>200</width>
        <height>200</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-200.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-32.png">
        <width>32</width>
        <height>32</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-32.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-32.xpm">
        <width>32</width>
        <height>32</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-32.xpm</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-48.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-48.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-48.xpm">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-48.xpm</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-64.png">
        <width>64</width>
        <height>64</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-64.png</location>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-64.xpm">
        <width>64</width>
        <height>64</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-64.xpm</location>
      </logo>
      <logo id="gnome-splash/gnome-splash.png">
        <width>503</width>
        <height>420</height>
        <location>/usr/share/pixmaps/splash/gnome-splash.png</location>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>210</textvcenter>
        <texthcenter>250</texthcenter>
        <gradient>True</gradient>        
      </logo>
      <logo id="rhgb/main-logo.png">
        <width>320</width>
        <height>396</height>
        <location>/usr/share/rhgb/main-logo.png</location>
        <textmaxwidth>320</textmaxwidth>
        <textvcenter>190</textvcenter>
        <texthcenter>160</texthcenter>        
      </logo>
      <logo id="rhgb/system-logo.png">
        <width>183</width>
        <height>45</height>
        <location>/usr/share/rhgb/system-logo.png</location>
        <textmaxwidth>150</textmaxwidth>
        <textvcenter>22</textvcenter>
        <texthcenter>90</texthcenter>        
      </logo>
      <logo id="gdm/themes/%s/background.png">
        <width>635</width>
        <height>480</height>
        <location>/usr/share/gdm/themes/%s/background.png</location>
        <gradient>True</gradient>        
      </logo>
      <logo id="gdm/themes/%s/GdmGreeterTheme.desktop">
        <location>/usr/share/gdm/themes/%s/GdmGreeterTheme.desktop</location>
      </logo>
      <logo id="gdm/themes/%s/%s.xml">
        <location>/usr/share/gdm/themes/%s/%s.xml</location>
      </logo>
    </logos>
    <logos version="11.2.0.66-1">
      <action type="insert" path=".">
        <logo id="anaconda/syslinux-vesa-splash.jpg">
          <location>/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg</location>
          <width>640</width>
          <height>480</height>
          <format>jpeg</format>
        </logo>
      </action>
    </logos>
  </logos-entries>
</locals>
'''

THEME_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE greeter SYSTEM "greeter.dtd">
<greeter>
  <item type="pixmap">
    <normal file="background.png"/>
    <pos x="0" y="0" width="100%" height="-75"/>
  </item>
  
  <item type="rect">
    <normal color="#000000"/>
    <pos x="0" y="-75" width="100%" height="75"/>
    <fixed>
      <item type="rect">
        <normal color="#ffffff"/>
        <pos x="0" y="4" width="100%" height="100%"/>
        <box orientation="horizontal" spacing="10" xpadding="10" ypadding="10">
          <item type="button" id="options_button">
            <pos width="100" height="50" />
            <stock type="options"/>
          </item>
        </box>
      </item>
    </fixed>
  </item>

  <item type="label" id="clock">
    <normal color="#000000" font="Sans 12"/>
    <pos x="-160" y="-37" anchor="e"/>
    <text>%c</text>
  </item>

  <item type="rect" id="caps-lock-warning">
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="75%" width="box" height="box"/>
    <box orientation="vertical" min-width="400" xpadding="10" ypadding="5" spacing="0">
      <item type="label">
        <normal color="#000000" font="Sans 12"/>
        <pos x="50%" anchor="n"/>
	<!-- Stock label for: You've got capslock on! -->
	<stock type="caps-lock-warning"/>
      </item>
    </box>
  </item>

  <item type="rect">
    <show type="timed"/>
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="25%" width="box" height="box"/>
    <box orientation="vertical" min-width="400" xpadding="10" ypadding="5" spacing="0">
      <item type="label" id="timed-label">
        <normal color="#000000" font="Sans 12"/>
        <pos x="50%" anchor="n"/>
	<!-- Stock label for: User %s will login in %d seconds -->
	<stock type="timed-label"/>
      </item>
    </box>
  </item>

  <item type="rect">
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="50%" width="box" height="box"/>
    <box orientation="vertical" min-width="340" xpadding="30" ypadding="30" spacing="10">
      <item type="label">
        <pos anchor="n" x="50%"/>
        <normal color="#000000" font="Sans 14"/>
	<!-- Stock label for: Welcome to %h -->
	<stock type="welcome-label"/>
      </item>
      <item type="label" id="pam-prompt">
        <pos anchor="nw" x="10%"/>
        <normal color="#000000" font="Sans 12"/>
	<!-- Stock label for: Username: -->
	<stock type="username-label"/>
      </item>
      <item type="rect">
	<normal color="#000000"/>
        <pos anchor="n" x="50%" height="24" width="80%"/>
	<fixed>
	  <item type="entry" id="user-pw-entry">
            <normal color="#000000" font="Sans 12"/>
            <pos anchor="nw" x="1" y="1" height="-2" width="-2"/>
	  </item>
	</fixed>
      </item>
      <item type="button" id="ok_button">
        <pos anchor="n" x="50%" height="32" width="50%"/>
        <stock type="ok"/>
      </item>
      <item type="button" id="cancel_button">
        <pos anchor="n" x="50%" height="32" width="50%"/>
        <stock type="startagain"/>
      </item>
      <item type="label" id="pam-message">
        <pos anchor="n" x="50%"/>
        <normal color="#000000" font="Sans 12"/>
	<text></text>
      </item>
    </box>
    <fixed>
      <item type="label" id="pam-error">
        <pos anchor="n" x="50%" y="110%"/>
        <normal color="#000000" font="Sans 12"/>
        <text></text>
      </item>
    </fixed>
  </item>
</greeter>
'''
