from gtk import *
import string
import gtk
import gobject
import sys
import functions
import rhpl.iconv
import os

##
## I18N
## 
import gettext
gettext.bindtextdomain ("firstboot", "/usr/share/locale")
gettext.textdomain ("firstboot")
_=gettext.gettext

class childWindow:
    #You must specify a runPriority for the order in which you wish your module to run
    runPriority = 15
    moduleName = (_("License Agreement"))

    def launch(self, doDebug = None):
        self.doDebug = doDebug
        if self.doDebug:
            print "initializing eula module"

        self.vbox = gtk.VBox()
        self.vbox.set_size_request(400, 200)

        msg = (_("License Agreement"))

        title_pix = functions.imageFromFile("workstation.png")

        internalVBox = gtk.VBox()
        internalVBox.set_border_width(10)
        internalVBox.set_spacing(5)

        textBuffer = gtk.TextBuffer()
        textView = gtk.TextView()
        textView.set_editable(False)
        textSW = gtk.ScrolledWindow()
        textSW.set_shadow_type(gtk.SHADOW_IN)
        textSW.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        textSW.add(textView)

        lang = os.environ.get("LANG", 'en_US')
        if len(string.split(lang, ".")) > 1:
            lang = string.split(lang, ".")[0]

        path = "/usr/share/eula/eula.%s" % lang
        if not os.path.exists(path):
		path = '/usr/share/eula/eula.en_US'

	lines = ["An error occurred reading %s. Do you concur?" % path]
        if os.path.exists(path):
            #If we don't have a translation for this locale, just open the English one
            lines = open(path).readlines()

        iter = textBuffer.get_iter_at_offset(0)

        for line in lines:
            textBuffer.insert(iter, line)
        textView.set_buffer(textBuffer)
            
        self.okButton = gtk.RadioButton(None, (_("_Yes, I agree to the License Agreement")))
        self.noButton = gtk.RadioButton(self.okButton, (_("N_o, I do not agree")))
        self.noButton.set_active(True)

        internalVBox.pack_start(textSW, True)
        internalVBox.pack_start(self.okButton, False)
        internalVBox.pack_start(self.noButton, False)
        
        self.vbox.pack_start(internalVBox, True, 5)
        return self.vbox, title_pix, msg

    def apply(self, notebook):
        if self.okButton.get_active() == True:
            return 0
        else:
            dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE,
                                    (_("Do you want to reread or reconsider the Licence Agreement?  " 
                                       "If not, please shut down the computer and remove this "
                                       "product from your system. ")))

            dlg.set_position(gtk.WIN_POS_CENTER)
            dlg.set_modal(True)

            continueButton = dlg.add_button(_("_Reread license"), 0)
            shutdownButton = dlg.add_button(_("_Shut down"), 1)
            continueButton.grab_focus()

            rc = dlg.run()
            dlg.destroy()

            if rc == 0:
                return None
            elif rc == 1:
                if self.doDebug:
                    print "shut down system"

                os.system("/sbin/halt")
                return None
                
