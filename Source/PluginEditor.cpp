#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& processor)
    : juce::AudioProcessorEditor(&processor)
{
    title.setText("Mono Delay", juce::dontSendNotification);
    title.setJustificationType(juce::Justification::centred);
    addAndMakeVisible(title);

    delayTimeLabel.setText("Delay Time (ms)", juce::dontSendNotification);
    delayTimeLabel.attachToComponent(&delayTimeSlider, true);
    addAndMakeVisible(delayTimeLabel);

    delayTimeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    delayTimeSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    delayTimeSlider.setRange(1.0, 3000.0, 1.0);
    addAndMakeVisible(delayTimeSlider);

    delayTimeAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.parameters, "delayTime", delayTimeSlider);

    setSize(420, 120);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto area = getLocalBounds();
    title.setBounds(area.removeFromTop(32));
    auto sliderArea = area.reduced(24, 16);
    delayTimeSlider.setBounds(sliderArea.removeFromTop(40).withTrimmedLeft(110));
}
