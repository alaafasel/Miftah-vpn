package com.miftah.vpn.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.miftah.vpn.ui.theme.Gold
import com.miftah.vpn.ui.theme.Navy
import com.miftah.vpn.ui.theme.SurfaceNavy
import com.miftah.vpn.ui.theme.TextMain
import com.miftah.vpn.ui.theme.TextMuted

@Composable
fun ActivationScreen(
    busy: Boolean,
    error: String?,
    onActivate: (String) -> Unit,
) {
    var code by remember { mutableStateOf("") }

    ScreenBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            LogoMark(size = 88.dp)
            Spacer(Modifier.height(18.dp))
            Text(
                text = "MIFTAH",
                color = TextMain,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 6.sp,
            )
            Spacer(Modifier.height(26.dp))
            Text(
                text = "تفعيل مفتاح",
                color = Gold,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "أدخل كود التفعيل الذي حصلت عليه من الإدارة",
                color = TextMuted,
                fontSize = 13.sp,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(22.dp))

            OutlinedTextField(
                value = code,
                onValueChange = { code = it.uppercase().filter { c -> c.isLetterOrDigit() || c == '-' }.take(24) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                enabled = !busy,
                placeholder = { Text("MFTH-XXXX-XXXX-XXXX-XXXX", color = TextMuted.copy(alpha = 0.6f)) },
                textStyle = TextStyle(
                    color = TextMain,
                    fontSize = 17.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 1.5.sp,
                    textAlign = TextAlign.Center,
                ),
                keyboardOptions = KeyboardOptions(
                    capitalization = KeyboardCapitalization.Characters,
                    imeAction = ImeAction.Done,
                ),
                keyboardActions = KeyboardActions(onDone = { if (!busy) onActivate(code) }),
                shape = RoundedCornerShape(14.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Gold,
                    unfocusedBorderColor = SurfaceNavy,
                    cursorColor = Gold,
                    focusedContainerColor = SurfaceNavy.copy(alpha = 0.5f),
                    unfocusedContainerColor = SurfaceNavy.copy(alpha = 0.5f),
                ),
            )

            ErrorBanner(error)

            Spacer(Modifier.height(20.dp))
            Button(
                onClick = { onActivate(code) },
                enabled = !busy && code.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Gold,
                    contentColor = Navy,
                    disabledContainerColor = Gold.copy(alpha = 0.35f),
                    disabledContentColor = Navy.copy(alpha = 0.6f),
                ),
            ) {
                if (busy) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Navy,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(text = "تفعيل", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(Modifier.height(18.dp))
            Text(
                text = "يتم التحقق من الكود عبر السيرفر وربطه بهذا الجهاز. لا يحتوي التطبيق على أي إعدادات اتصال قبل التفعيل.",
                color = TextMuted,
                fontSize = 12.sp,
                textAlign = TextAlign.Center,
            )
        }
    }
}
