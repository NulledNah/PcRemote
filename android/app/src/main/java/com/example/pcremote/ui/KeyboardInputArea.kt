package com.example.pcremote.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private const val MAX_FIELD_LENGTH = 300

private fun isWordBoundary(c: Char): Boolean =
    c == ' ' || c == '\n' || c == '\t' || c == '.' || c == ',' ||
    c == ';' || c == ':' || c == '!' || c == '?' || c == ')' || c == '('

@Composable
fun KeyboardInputArea(
    onKeyEvent: (Int, Boolean) -> Unit,
    onComboText: (CharSequence) -> Unit,
    onEnter: () -> Unit,
    onBackspace: () -> Unit,
    useAutocorrect: Boolean = true,
    modifier: Modifier = Modifier
) {
    val focusRequester = remember { FocusRequester() }
    val keyboard = LocalSoftwareKeyboardController.current
    var textFieldValue by remember { mutableStateOf(TextFieldValue("")) }

    val keyboardType = if (useAutocorrect) KeyboardType.Text else KeyboardType.Ascii

    Box(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceContainerHigh)
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth()
        ) {
            BasicTextField(
                value = textFieldValue,
                onValueChange = { newValue ->
                    val oldText = textFieldValue.text
                    val newText = newValue.text

                    var commonLen = 0
                    while (commonLen < oldText.length &&
                        commonLen < newText.length &&
                        oldText[commonLen] == newText[commonLen]
                    ) {
                        commonLen++
                    }

                    val removed = oldText.length - commonLen
                    val added = newText.substring(commonLen)

                    repeat(removed) { onBackspace() }

                    if (added.isNotEmpty()) {
                        onComboText(added)
                    }

                    val finalText = if (newText.length > MAX_FIELD_LENGTH) {
                        var boundaries = mutableListOf<Int>()
                        for (i in newText.indices) {
                            if (isWordBoundary(newText[i])) {
                                boundaries.add(i)
                            }
                        }
                        val cutIdx = if (boundaries.size >= 2) {
                            boundaries[boundaries.size - 2] + 1
                        } else if (boundaries.size == 1 && boundaries[0] < newText.length - 1) {
                            boundaries[0] + 1
                        } else {
                            (newText.length - 50).coerceAtLeast(0)
                        }
                        val keep = newText.substring(cutIdx)
                        TextFieldValue(keep, TextRange(keep.length))
                    } else {
                        newValue
                    }

                    textFieldValue = finalText
                },
                modifier = Modifier
                    .weight(1f)
                    .focusRequester(focusRequester)
                    .onFocusChanged { state ->
                        if (state.isFocused) {
                            keyboard?.show()
                        }
                    },
                textStyle = TextStyle(
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.onSurface
                ),
                cursorBrush = SolidColor(MaterialTheme.colorScheme.primary),
                keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
                singleLine = true,
                decorationBox = { innerTextField ->
                    Box {
                        if (textFieldValue.text.isEmpty()) {
                            Text(
                                text = "Tap to type...",
                                fontSize = 16.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
                            )
                        }
                        innerTextField()
                    }
                }
            )

            Text(
                text = "\u2328",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 8.dp)
            )

            Text(
                text = "\u23CE",
                fontSize = 20.sp,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .padding(start = 8.dp)
                    .background(
                        MaterialTheme.colorScheme.surfaceContainerHighest,
                        shape = MaterialTheme.shapes.small
                    )
                    .padding(horizontal = 10.dp, vertical = 6.dp)
                    .clickable(
                        indication = null,
                        interactionSource = remember { MutableInteractionSource() }
                    ) { onEnter() }
            )

            if (textFieldValue.text.isNotEmpty()) {
                Text(
                    text = "\u2715",
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier
                        .padding(start = 6.dp)
                        .background(
                            MaterialTheme.colorScheme.surfaceContainerHighest,
                            shape = MaterialTheme.shapes.small
                        )
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                        .clickable(
                        indication = null,
                        interactionSource = remember { MutableInteractionSource() }
                    ) {
                        textFieldValue = TextFieldValue("")
                    }
                )
            }
        }
    }
}
