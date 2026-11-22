// SPDX-License-Identifier: Apache-2.0
package de.eibelucas.kiosksip.nativephone;

import android.content.Context;
import android.graphics.drawable.Drawable;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.*;
import me.jxl.kiosk.plugins.*;
import java.util.ArrayList;
import java.util.List;

/** One persistent native view: the floating button expands in place, without a WebView. */
final class FloatingDialer implements OverlayFactory {
    interface Actions { void toggle();void dial(String number);void hangup();void answer();void mute(); }
    private final DialerModel model;
    private final Actions actions;
    private final PhoneText text;
    private LinearLayout root, panel, input, keypad;
    private ScrollView scroll;
    private Button chip,call,end,accept,mute,backspace,collapse;
    private TextView status,peer;
    private EditText number;
    private final List<Button> digits=new ArrayList<>();
    private KsTheme theme;
    private volatile Context audioContext;
    private boolean editing;
    /** Small screens (under 600 dp high, such as a 480 x 480 wall panel): one header line, smaller keys, Call beside the number. */
    private boolean compact;
    /** The overlay's bottom inset in dp, so the panel never grows under the phone button. */
    private int bottomInset=88;
    void setBottomInset(int dp){bottomInset=dp;}
    /** Phone button on the left: panel and button line up on the left edge, not the right. */
    private boolean left;
    void setLeft(boolean value){left=value;}
    static boolean isCompact(int heightPx,float density){return heightPx<600*density;}
    /** Height left for the panel: screen minus top inset, phone button with its margin and bottom inset. */
    static int panelLimit(int heightPx,float density,int bottomDp){return Math.max(Math.round(100*density),heightPx-Math.round((bottomDp+12+56+8)*density));}
    FloatingDialer(DialerModel model,Actions actions,PhoneText text){this.model=model;this.actions=actions;this.text=text;}
    public View create(Context context,KsTheme theme){
        audioContext=context.getApplicationContext();
        this.theme=theme;digits.clear();
        root=new LinearLayout(context);root.setOrientation(LinearLayout.VERTICAL);root.setGravity(left?Gravity.START:Gravity.END);
        android.util.DisplayMetrics metrics=context.getResources().getDisplayMetrics();
        compact=isCompact(metrics.heightPixels,theme.px(100)/100f);
        int key=compact?40:48;
        panel=new LinearLayout(context);panel.setOrientation(LinearLayout.VERTICAL);
        if(compact)panel.setPadding(theme.px(12),theme.px(6),theme.px(12),theme.px(8));else panel.setPadding(theme.px(16),theme.px(12),theme.px(16),theme.px(12));
        LinearLayout header=new LinearLayout(context);header.setGravity(Gravity.CENTER_VERTICAL);
        status=new TextView(context);status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        if(compact){
            // The status line ("Ready · Extension …") replaces the title, so the header costs one row.
            status.setMaxLines(2);status.setEllipsize(android.text.TextUtils.TruncateAt.END);
            header.addView(status,new LinearLayout.LayoutParams(0,-2,1));
        }else{
            TextView title=new TextView(context);title.setText(text.get("Phone"));theme.styleText(title,18,500,"onSurface");
            header.addView(title,new LinearLayout.LayoutParams(0,-2,1));
        }
        collapse=button(context,"Close","mdi:chevron-down");collapse.setText("");collapse.setOnClickListener(v->actions.toggle());header.addView(collapse,new LinearLayout.LayoutParams(theme.px(key),theme.px(key)));panel.addView(header);
        if(!compact){status.setPadding(0,theme.px(6),0,theme.px(10));panel.addView(status);}
        peer=new TextView(context);panel.addView(peer);
        input=new LinearLayout(context);input.setGravity(Gravity.CENTER_VERTICAL);
        number=new EditText(context);number.setSingleLine(true);number.setHint(text.get("Dial a number"));number.setInputType(InputType.TYPE_CLASS_PHONE);number.setSelectAllOnFocus(false);
        number.setShowSoftInputOnFocus(false);
        // EditText's default vertical padding plus font padding is taller than the field, which cut the digits off at the top.
        number.setIncludeFontPadding(false);number.setPadding(theme.px(4),0,theme.px(4),0);number.setGravity(Gravity.CENTER_VERTICAL|Gravity.START);
        number.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(20)});
        number.setContentDescription(text.get("Destination number"));number.addTextChangedListener(new android.text.TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int count,int after){}public void onTextChanged(CharSequence s,int st,int before,int count){if(!editing&&!model.active()){model.number=s.toString();call.setEnabled(model.canDial());}}public void afterTextChanged(android.text.Editable e){}});
        input.addView(number,new LinearLayout.LayoutParams(0,theme.px(compact?44:52),1));
        backspace=button(context,"Delete digit","mdi:backspace-outline");backspace.setText("");backspace.setOnClickListener(v->{model.delete();refresh();});input.addView(backspace,new LinearLayout.LayoutParams(theme.px(key),theme.px(key)));panel.addView(input);
        String[] keys={"1","2","3","4","5","6","7","8","9","*","0","#"};
        keypad=new LinearLayout(context);keypad.setOrientation(LinearLayout.VERTICAL);panel.addView(keypad);
        for(int row=0;row<4;row++){
            LinearLayout line=new LinearLayout(context);
            for(int col=0;col<3;col++){String digit=keys[row*3+col];Button b=button(context,digit,null);b.setOnClickListener(v->{model.digit(digit);refresh();});if(digit.equals("0")){b.setContentDescription(text.get("0, hold for plus"));b.setOnLongClickListener(v->{model.plus();refresh();return true;});}LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,theme.px(key),1);int gap=theme.px(compact?2:3);p.setMargins(gap,gap,gap,gap);line.addView(b,p);digits.add(b);}
            keypad.addView(line);
        }
        call=button(context,"Call","mdi:phone");call.setOnClickListener(v->actions.dial(number.getText().toString()));
        if(compact){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(theme.px(56),theme.px(key));p.leftMargin=theme.px(6);input.addView(call,p);}
        else panel.addView(call,full());
        accept=button(context,"Answer","mdi:phone");accept.setOnClickListener(v->actions.answer());panel.addView(accept,full());
        mute=button(context,"Mute","mdi:microphone-off");mute.setOnClickListener(v->actions.mute());panel.addView(mute,full());
        end=button(context,"Hang up","mdi:phone-hangup");end.setOnClickListener(v->actions.hangup());panel.addView(end,full());
        scroll=new ScrollView(context){protected void onMeasure(int w,int h){int limit=panelLimit(context.getResources().getDisplayMetrics().heightPixels,theme.px(100)/100f,bottomInset);if(View.MeasureSpec.getMode(h)!=View.MeasureSpec.UNSPECIFIED)limit=Math.min(limit,View.MeasureSpec.getSize(h));super.onMeasure(w,View.MeasureSpec.makeMeasureSpec(limit,View.MeasureSpec.AT_MOST));}};
        scroll.setFillViewport(false);scroll.addView(panel);
        int width=Math.min(theme.px(304),context.getResources().getDisplayMetrics().widthPixels-theme.px(32));
        root.addView(scroll,new LinearLayout.LayoutParams(Math.max(1,width),-2));
        chip=button(context,"Open phone","mdi:phone");chip.setOnClickListener(v->actions.toggle());
        LinearLayout.LayoutParams chipParams=new LinearLayout.LayoutParams(theme.px(56),theme.px(56));chipParams.topMargin=theme.px(8);root.addView(chip,chipParams);
        style(theme);refresh();return root;
    }
    private LinearLayout.LayoutParams full(){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,theme.px(compact?44:48));p.topMargin=theme.px(compact?6:8);return p;}
    private Button button(Context c,String label,String icon){Button b=new Button(c);b.setAllCaps(false);b.setText(text.get(label));b.setContentDescription(text.get(label));b.setMinWidth(0);b.setMinimumWidth(0);b.setPadding(theme.px(8),0,theme.px(8),0);if(icon!=null){Drawable d=theme.icon(icon,"onSurface");if(d!=null){b.setCompoundDrawablesWithIntrinsicBounds(d,null,null,null);}}theme.stylePill(b,false);return b;}
    private void iconOnly(Button button,String icon,boolean filled){
        // Foreground gravity centers the icon in the actual touch target, independent of text layout.
        button.setText("");button.setCompoundDrawables(null,null,null,null);
        button.setPadding(0,0,0,0);button.setMinWidth(0);button.setMinimumWidth(0);button.setMinHeight(0);button.setMinimumHeight(0);
        Drawable image=theme.icon(icon,filled?"onPrimary":"primary");
        if(image==null)image=theme.icon("mdi:phone",filled?"onPrimary":"primary");
        button.setForeground(image);button.setForegroundGravity(Gravity.CENTER);
    }
    void refresh(){
        if(root==null)return;
        scroll.setVisibility(model.expanded?View.VISIBLE:View.GONE);
        editing=true;if(!number.getText().toString().equals(model.number)){number.setText(model.number);number.setSelection(number.length());}editing=false;
        number.setEnabled(!model.active());backspace.setEnabled(!model.active());
        input.setVisibility(model.active()?View.GONE:View.VISIBLE);
        keypad.setVisibility(model.active()?View.GONE:View.VISIBLE);
        status.setText(model.label());peer.setText(model.active()?model.peer:"");peer.setVisibility(model.active()?View.VISIBLE:View.GONE);
        for(Button digit:digits)digit.setVisibility(model.active()?View.GONE:View.VISIBLE);
        call.setVisibility(model.active()?View.GONE:View.VISIBLE);call.setEnabled(model.canDial());
        accept.setVisibility(model.state.equals("incoming")?View.VISIBLE:View.GONE);
        mute.setVisibility(model.state.equals("connected")?View.VISIBLE:View.GONE);mute.setText(text.get(model.muted?"Unmute microphone":"Mute"));mute.setContentDescription(text.get(model.muted?"Unmute microphone":"Mute"));mute.setSelected(model.muted);
        end.setVisibility(model.active()?View.VISIBLE:View.GONE);end.setText(text.get(model.state.equals("incoming")?"Decline":model.state.equals("connected")?"Hang up":"Cancel"));end.setContentDescription(end.getText());
        chip.setContentDescription(text.get(model.active()?"Show call":"Open phone"));
        if(chip.isSelected()!=model.active()){chip.setSelected(model.active());iconOnly(chip,model.active()?"mdi:phone-in-talk":"mdi:phone",true);}
        chip.setAlpha(model.registered||model.active()?1f:.6f);
        root.requestLayout();
    }
    private void style(KsTheme next){theme=next;if(panel==null)return;panel.setBackground(theme.card());theme.styleText(status,13,400,"onSurfaceVariant");theme.styleText(peer,22,500,"onSurface");theme.styleText(number,24,400,"onSurface");for(Button b:digits)theme.stylePill(b,false);for(Button b:new Button[]{call,accept,chip})theme.stylePill(b,true);theme.stylePill(mute,false);theme.stylePill(end,false);end.setTextColor(theme.color("error"));theme.stylePill(collapse,false);theme.stylePill(backspace,false);iconOnly(chip,model.active()?"mdi:phone-in-talk":"mdi:phone",true);iconOnly(collapse,"mdi:chevron-down",false);iconOnly(backspace,"mdi:backspace-outline",false);
        if(compact){
            // stylePill sets a 44 dp minimum height, 96 dp minimum width and 12 dp padding; undo that for the small keys.
            for(Button b:digits){b.setMinHeight(0);b.setMinimumHeight(0);b.setMinWidth(0);b.setMinimumWidth(0);b.setPadding(0,0,0,0);}
            theme.styleText(status,13,500,"onSurface");theme.styleText(number,22,400,"onSurface");
            iconOnly(call,"mdi:phone",true);
        }
        number.setIncludeFontPadding(false);number.setPadding(theme.px(4),0,theme.px(4),0);
    }
    public void onThemeChanged(View view,KsTheme theme){if(view==root){style(theme);refresh();}}
    public void onDestroy(View view){if(view==root){root=null;panel=null;digits.clear();}}
    Context audioContext(){return audioContext;}
}
