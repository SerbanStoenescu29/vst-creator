#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class VstAiDemoAudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor&);
    ~VstAiDemoAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    VstAiDemoAudioProcessor& processorRef;
    
    juce::Label titleLabel;
    juce::Label driveLabel;
    juce::Label toneLabel;
    juce::Slider driveSlider;
    juce::Slider toneSlider;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> driveAttachment;
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> toneAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VstAiDemoAudioProcessorEditor)
};
