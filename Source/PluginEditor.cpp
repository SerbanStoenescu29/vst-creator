#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& p)
    : juce::AudioProcessorEditor(&p), processor(p)
{
    // Delay Slider (hidden, for parameter attachment only)
    delaySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    delaySlider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
    delaySlider.setRange(1.0, 1000.0, 0.01);
    delaySlider.setVisible(false);
    addAndMakeVisible(delaySlider);
    delayAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.parameters, "delayTime", delaySlider);

    // Wet/Dry Slider (hidden, for parameter attachment only)
    wetDrySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    wetDrySlider.setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
    wetDrySlider.setRange(0.0, 1.0, 0.001);
    wetDrySlider.setVisible(false);
    addAndMakeVisible(wetDrySlider);
    wetDryAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.parameters, "wetDry", wetDrySlider);

    setSize(480, 120);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::white);

    auto area = getLocalBounds();
    auto sliderHeight = 32;
    auto sliderWidth = getWidth() * 0.55f;
    auto labelGap = 16;
    auto labelWidth = 100;
    auto sliderY1 = area.getY() + area.getHeight() / 4 - sliderHeight / 2;
    auto sliderY2 = area.getY() + 3 * area.getHeight() / 4 - sliderHeight / 2;
    auto sliderX = area.getX() + (getWidth() - sliderWidth - labelGap - labelWidth) / 2;

    // --- Draw Delay Slider ---
    {
        float y = (float)sliderY1 + sliderHeight / 2.0f;
        float x1 = (float)sliderX;
        float x2 = (float)(sliderX + sliderWidth);
        g.setColour(juce::Colours::black);
        g.drawLine(x1, y, x2, y, 1.0f);

        // Draw handle as diagonal line
        float norm = (float)((delaySlider.getValue() - delaySlider.getMinimum()) /
                             (delaySlider.getMaximum() - delaySlider.getMinimum()));
        float handleX = x1 + norm * (x2 - x1);
        float handleY1 = y - 10.0f;
        float handleY2 = y + 10.0f;
        g.drawLine(handleX - 7.0f, handleY1, handleX + 7.0f, handleY2, 2.0f);

        // Draw label
        g.setFont(juce::Font("Arial", 18.0f, juce::Font::plain));
        g.setColour(juce::Colours::black);
        g.drawText("Delay (ms)", (int)(x2 + labelGap), (int)(y - 12), labelWidth, 24, juce::Justification::centredLeft);
    }

    // --- Draw Wet/Dry Slider ---
    {
        float y = (float)sliderY2 + sliderHeight / 2.0f;
        float x1 = (float)sliderX;
        float x2 = (float)(sliderX + sliderWidth);
        g.setColour(juce::Colours::black);
        g.drawLine(x1, y, x2, y, 1.0f);

        // Draw handle as diagonal line
        float norm = (float)((wetDrySlider.getValue() - wetDrySlider.getMinimum()) /
                             (wetDrySlider.getMaximum() - wetDrySlider.getMinimum()));
        float handleX = x1 + norm * (x2 - x1);
        float handleY1 = y - 10.0f;
        float handleY2 = y + 10.0f;
        g.drawLine(handleX - 7.0f, handleY1, handleX + 7.0f, handleY2, 2.0f);

        // Draw label
        g.setFont(juce::Font("Arial", 18.0f, juce::Font::plain));
        g.setColour(juce::Colours::black);
        g.drawText("wet/dry", (int)(x2 + labelGap), (int)(y - 12), labelWidth, 24, juce::Justification::centredLeft);
    }
}

void VstAiDemoAudioProcessorEditor::resized()
{
    // Sliders are not visible, but must be sized for parameter attachment
    auto area = getLocalBounds();
    auto sliderHeight = 32;
    auto sliderWidth = getWidth() * 0.55f;
    auto labelGap = 16;
    auto labelWidth = 100;
    auto sliderX = area.getX() + (getWidth() - sliderWidth - labelGap - labelWidth) / 2;
    auto sliderY1 = area.getY() + area.getHeight() / 4 - sliderHeight / 2;
    auto sliderY2 = area.getY() + 3 * area.getHeight() / 4 - sliderHeight / 2;

    delaySlider.setBounds((int)sliderX, sliderY1, (int)sliderWidth, sliderHeight);
    wetDrySlider.setBounds((int)sliderX, sliderY2, (int)sliderWidth, sliderHeight);
}
