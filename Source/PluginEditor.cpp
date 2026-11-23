#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& processor)
    : juce::AudioProcessorEditor(&processor)
{
    // Title label
    titleLabel.setText("VstAi Reverb", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setFont(juce::Font(24.0f).boldened());
    addAndMakeVisible(titleLabel);

    // Decay label
    decayLabel.setText("Decay", juce::dontSendNotification);
    decayLabel.setJustificationType(juce::Justification::centred);
    decayLabel.setFont(juce::Font(14.0f));
    addAndMakeVisible(decayLabel);

    // Decay slider (knob)
    decaySlider.setSliderStyle(juce::Slider::RotaryVerticalDrag);
    decaySlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    decaySlider.setColour(juce::Slider::rotarySliderFillColourId, juce::Colours::cyan);
    decaySlider.setColour(juce::Slider::rotarySliderOutlineColourId, juce::Colours::white);
    addAndMakeVisible(decaySlider);

    // Attach slider to parameter
    decayAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.getAPVTS(), "decay", decaySlider);

    setSize(420, 300);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto bounds = getLocalBounds();
    auto margin = 20;

    // Title at top
    titleLabel.setBounds(bounds.removeFromTop(50).reduced(margin, 0));

    // Decay control in center
    auto sliderArea = bounds.reduced(margin);
    decayLabel.setBounds(sliderArea.removeFromTop(30));
    decaySlider.setBounds(sliderArea.reduced(40, 0));
}
